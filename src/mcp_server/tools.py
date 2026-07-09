# kasa/src/mcp_server/tools.py

"""
MCP (Model Context Protocol) sunucusu tarafından ajanlara sunulacak
araçların (tools) implementasyonu. Gerçek vault DB operasyonlarını içerir.

Her araç çağrısı: izin kontrolü (permissions tablosu) → işlem → audit kaydı.
"""

import json
import time
import sqlite3
from ..vault.database import Vault


class VaultTools:
    def __init__(self, vault: Vault, agent_id: str):
        self.vault = vault
        self.agent_id = agent_id
        self.audit_chain = vault.audit_chain

    def _db(self) -> sqlite3.Connection:
        """Vault'un aktif DB bağlantısını döndürür."""
        return self.vault.get_connection()

    def _check_permission(self, scope: str) -> bool:
        """
        permissions tablosundan ajan izni kontrol eder (deny-by-default).
        MVP-0: 'system' ajanına her şey açık; diğerleri DB'den kontrol edilir.
        """
        if self.agent_id == "system":
            return True
        cursor = self._db().cursor()
        cursor.execute(
            "SELECT 1 FROM permissions WHERE agent_id=? AND scope=? AND revoked_at IS NULL",
            (self.agent_id, scope)
        )
        return cursor.fetchone() is not None

    def grant_permission(self, scope: str) -> None:
        """Ajan için belirli bir kapsam izni verir (sistem aracı, MVP-0 helper).

        GUVENLIK: izin yukseltmeyi onlemek icin 'admin:grant' kapsami gerekir.
        Ag katmani bunu zaten PUBLIC_TOOLS allow-list'i disinda tutar (C7); bu, in-process
        cagrilar icin derinlemesine savunmadir. 'system' (in-process distill/bakim) muaftir.
        """
        if not self._check_permission("admin:grant"):
            raise PermissionError(f"Ajan '{self.agent_id}' icin izin verme (grant) yetkisi yok.")
        cursor = self._db().cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO permissions (agent_id, scope, granted_at) VALUES (?,?,?)",
            (self.agent_id, scope, time.time())
        )
        self._db().commit()

    def profile_read(self, scope: str) -> dict:
        """
        Profil veritabanından bir veya daha fazla anahtar-değer çiftini okur.

        Args:
            scope: Okunacak anahtar (örn: 'user.name') veya kapsam (örn: 'user.*').

        Returns:
            Okunan verileri içeren bir sözlük.
        """
        action = "profile_read"
        details = {"scope": scope}
        
        if not self._check_permission(f"profile:read:{scope}"):
            self.audit_chain.record(self.agent_id, action, {**details, "result": "permission_denied"})
            raise PermissionError(f"Ajan '{self.agent_id}' için '{scope}' okuma izni yok.")

        cursor = self._db().cursor()
        # scope 'user.*' gibi wildcard içeriyorsa prefix araması yap
        if scope.endswith('*'):
            prefix = scope[:-1]
            cursor.execute(
                "SELECT key, value, provenance, updated_at FROM profile WHERE key LIKE ?",
                (prefix + '%',)
            )
        else:
            cursor.execute(
                "SELECT key, value, provenance, updated_at FROM profile WHERE key = ?",
                (scope,)
            )
        rows = cursor.fetchall()
        data = [
            {"key": r[0], "value": json.loads(r[1]), "provenance": json.loads(r[2]), "updated_at": r[3]}
            for r in rows
        ]
        result = {"status": "success", "count": len(data), "data": data}

        self.audit_chain.record(self.agent_id, action, {**details, "result": "success", "count": len(data)})
        return result

    def profile_write(self, key: str, value: any, provenance: list) -> dict:
        """
        Profil veritabanına yeni bir damıtılmış bilgi yazar veya günceller.

        Args:
            key: Yazılacak bilginin anahtarı.
            value: Bilginin değeri (JSON-serileştirilebilir).
            provenance: Bu bilginin hangi olaylardan (event) türetildiğini gösteren ID listesi.

        Returns:
            İşlem sonucunu belirten bir sözlük.
        """
        action = "profile_write"
        details = {"key": key, "value": value, "provenance": provenance}

        if not self._check_permission("profile:write"):
            self.audit_chain.record(self.agent_id, action, {**details, "result": "permission_denied"})
            raise PermissionError(f"Ajan '{self.agent_id}' için yazma izni yok.")

        now = time.time()
        conn = self._db()
        cursor = conn.cursor()
        # Mevcut satır varsa ID'sini al — supersedes zinciri için
        cursor.execute("SELECT id FROM profile WHERE key = ?", (key,))
        old_row = cursor.fetchone()
        supersedes_id = old_row[0] if old_row else None

        cursor.execute(
            """INSERT OR REPLACE INTO profile (id, key, value, provenance, supersedes, created_at, updated_at)
               SELECT old.id, ?, ?, ?, ?, COALESCE(old.created_at, ?), ?
               FROM (SELECT NULL as id, NULL as created_at) as fallback
               LEFT JOIN profile old ON old.key = ?""",
            (key, json.dumps(value), json.dumps(provenance), supersedes_id, now, now, key)
        )
        conn.commit()
        result = {"status": "success", "key": key}

        self.audit_chain.record(self.agent_id, action, {**details, "result": "success"})
        return result

    def forget(self, topic: str) -> dict:
        """
        Belirli bir konuyla ilgili tüm bilgileri Kasa'dan kalıcı olarak siler.

        Args:
            topic: Silinecek konu.

        Returns:
            İşlem sonucunu belirten bir sözlük.
        """
        action = "forget"
        details = {"topic": topic}

        if not self._check_permission("admin:forget"):
            self.audit_chain.record(self.agent_id, action, {**details, "result": "permission_denied"})
            raise PermissionError(f"Ajan '{self.agent_id}' için 'forget' işlemi izni yok.")

        conn = self._db()
        cursor = conn.cursor()
        # Profile satırlarını sil (anahtar prefix eşleşmesi)
        cursor.execute("DELETE FROM profile WHERE key LIKE ?", (topic + '%',))
        profile_deleted = cursor.rowcount
        # Ham event'leri de sil (TTL'den bağımsız — gerçek silme garantisi)
        cursor.execute("DELETE FROM events WHERE content LIKE ?", (f'%{topic}%',))
        events_deleted = cursor.rowcount
        # Audit zincirinde tombstone kaydı
        self.audit_chain.record(self.agent_id, "forget_tombstone",
                                {"topic": topic, "profile_deleted": profile_deleted,
                                 "events_deleted": events_deleted})
        conn.commit()
        result = {"status": "success", "topic": topic,
                  "profile_deleted": profile_deleted, "events_deleted": events_deleted}

        self.audit_chain.record(self.agent_id, action, {**details, "result": "success"})
        return result

    def audit_read(self, start_index: int = 0, count: int = 100) -> dict:
        """
        Denetim (audit) zincirinden kayıtları okur.

        Args:
            start_index: Başlangıç kaydı.
            count: Okunacak kayıt sayısı.

        Returns:
            Denetim kayıtlarını içeren bir sözlük.
        """
        action = "audit_read"
        scope = f"audit:read:{start_index}:{count}"
        details = {"start_index": start_index, "count": count}

        if not self._check_permission("audit:read"):
            raise PermissionError(f"Ajan '{self.agent_id}' için denetim okuma izni yok.")

        cursor = self._db().cursor()
        cursor.execute(
            "SELECT id, timestamp, agent_id, action, details, entry_hash FROM audit ORDER BY id DESC LIMIT ? OFFSET ?",
            (count, start_index)
        )
        rows = cursor.fetchall()
        data = [
            {"id": r[0], "timestamp": r[1], "agent_id": r[2], "action": r[3],
             "details": json.loads(r[4]), "entry_hash": r[5]}
            for r in rows
        ]
        result = {"status": "success", "count": len(data), "records": data}

        self.audit_chain.record(self.agent_id, action, {**details, "result": "success"})
        return result

    def prune_expired_events(self) -> dict:
        """Süresi dolmuş ve damıtılmış event'leri siler; ardından VACUUM çalıştırır."""
        if not self._check_permission("admin:prune"):
            raise PermissionError(f"Ajan '{self.agent_id}' için prune izni yok.")

        conn = self._db()
        now = time.time()
        cursor = conn.cursor()
        # Sadece distilled=1 olan ve TTL'si geçmiş satırlar silinir
        cursor.execute(
            "DELETE FROM events WHERE ttl_expiry < ? AND distilled = 1",
            (now,)
        )
        deleted = cursor.rowcount
        conn.commit()
        try:
            conn.execute("VACUUM")
        except Exception:
            pass  # WAL modunda veya başka bağlantı varsa sessizce atla

        self.audit_chain.record(self.agent_id, "prune_expired_events",
                                {"deleted": deleted, "pruned_at": now})
        return {"status": "success", "deleted": deleted}

    def event_ingest(self, source: str, type: str, content: dict, ttl_days: int = 30) -> dict:
        """
        Olayları Vault'a alır ve TTL süresine göre saklar.

        Args:
            source: Olayın kaynağı.
            type: Olayın türü.
            content: Olayın içeriği (JSON-serileştirilebilir).
            ttl_days: Olayın saklanma süresi (gün cinsinden).

        Returns:
            İşlem sonucunu belirten bir sözlük.
        """
        action = "event_ingest"
        details = {"source": source, "type": type, "content": content, "ttl_days": ttl_days}

        if not self._check_permission("events:write"):
            self.audit_chain.record(self.agent_id, action, {**details, "result": "permission_denied"})
            raise PermissionError(f"Ajan '{self.agent_id}' için olay yazma izni yok.")

        if len(source) > 64 or len(type) > 64:
            self.audit_chain.record(self.agent_id, action, {**details, "result": "invalid_input"})
            raise ValueError("Kaynak ve tür en fazla 64 karakter olmalıdır.")

        if not (1 <= ttl_days <= 365):
            self.audit_chain.record(self.agent_id, action, {**details, "result": "invalid_input"})
            raise ValueError("TTL gün sayısı 1 ile 365 arasında olmalıdır.")

        now = time.time()
        ttl_expiry = now + ttl_days * 86400
        conn = self._db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO events (timestamp, session_id, source, type, content, ttl_expiry) VALUES (?, ?, ?, ?, ?, ?)",
            (now, self.agent_id, source, type, json.dumps(content), ttl_expiry)
        )
        event_id = cursor.lastrowid
        conn.commit()

        self.audit_chain.record(self.agent_id, action, {**details, "result": "success", "event_id": event_id})
        return {"status": "success", "event_id": event_id}
