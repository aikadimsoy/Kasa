# kasa/src/mcp_server/tools.py

"""
MCP (Model Context Protocol) sunucusu tarafından ajanlara sunulacak
araçların (tools) implementasyonu. Gerçek vault DB operasyonlarını içerir.

Her araç çağrısı: izin kontrolü (permissions tablosu) → işlem → audit kaydı.
"""

import json
import time
import hashlib
import sqlite3
from ..vault.database import Vault
from ..vault import cell_crypt


def _digest(value) -> str:
    """Audit'e ham deger yerine yazilacak deterministik ozet (sir degismez zincire girmez)."""
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


class VaultTools:
    def __init__(self, vault: Vault, agent_id: str):
        self.vault = vault
        self.agent_id = agent_id
        self.audit_chain = vault.audit_chain

    def _db(self) -> sqlite3.Connection:
        """Vault'un aktif DB bağlantısını döndürür."""
        return self.vault.get_connection()

    def _key(self) -> bytes:
        """L2 hucre-sifreleme anahtari (DPAPI-korumali _db_key)."""
        return self.vault._db_key

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
        # L2: value at-rest sifreli -> decrypt (AAD = profile|value|key). Legacy plaintext seffaf gecer.
        key_bytes = self._key()
        data = [
            {"key": r[0],
             "value": json.loads(cell_crypt.decrypt_cell(r[1], key_bytes, cell_crypt.aad_profile(r[0]))),
             "provenance": json.loads(r[2]), "updated_at": r[3]}
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
        # L2: audit'e ham `value` YAZILMAZ (tools.py:109 yan-kanal) -> digest. provenance ID'ler, plaintext.
        details = {"key": key, "value": _digest(value), "provenance": provenance}

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

        # L2: value at-rest AES-GCM sifrelenir (AAD = profile|value|key). provenance = event-ID'ler, plaintext.
        enc_value = cell_crypt.encrypt_cell(json.dumps(value), self._key(), cell_crypt.aad_profile(key))
        cursor.execute(
            """INSERT OR REPLACE INTO profile (id, key, value, provenance, supersedes, created_at, updated_at)
               SELECT old.id, ?, ?, ?, ?, COALESCE(old.created_at, ?), ?
               FROM (SELECT NULL as id, NULL as created_at) as fallback
               LEFT JOIN profile old ON old.key = ?""",
            (key, enc_value, json.dumps(provenance), supersedes_id, now, now, key)
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
        # Profile satırlarını sil (anahtar plaintext -> prefix eşleşmesi calisir)
        cursor.execute("DELETE FROM profile WHERE key LIKE ?", (topic + '%',))
        profile_deleted = cursor.rowcount

        # L2: events.content SIFRELI -> `content LIKE` sessizce 0 satir siler (false-PASS sinifi).
        # Cozum: DECRYPT-SCAN by id. Her satiri coz, topic'i Python'da esle, id ile sil.
        # forget owner-gated/nadir + events TTL-prune'lu -> tam-tarama maliyeti kabul edilebilir.
        key_bytes = self._key()
        cursor.execute("SELECT id, content FROM events")
        rows = cursor.fetchall()
        events_scanned = len(rows)
        match_ids = []
        for r in rows:
            try:
                plain = cell_crypt.decrypt_cell(r["content"], key_bytes, cell_crypt.aad_event())
            except Exception:
                plain = ""  # cozulemeyen satir eslesmeye dahil edilmez (ama tarandi sayilir)
            if topic in plain:
                match_ids.append(r["id"])
        events_matched = len(match_ids)
        if match_ids:
            placeholders = ",".join("?" * len(match_ids))
            cursor.execute(f"DELETE FROM events WHERE id IN ({placeholders})", match_ids)
            events_deleted = cursor.rowcount
        else:
            events_deleted = 0

        # SESSIZ-SIFIR GUARD: eslesme bulundu ama silinmediyse artik sessizce "success" DONMEZ.
        if events_matched != events_deleted:
            raise RuntimeError(f"forget guard ihlali: matched={events_matched} != deleted={events_deleted}")

        # Audit zincirinde tombstone kaydı (scanned/matched/deleted ayri raporlanir)
        self.audit_chain.record(self.agent_id, "forget_tombstone",
                                {"topic": topic, "profile_deleted": profile_deleted,
                                 "events_scanned": events_scanned, "events_matched": events_matched,
                                 "events_deleted": events_deleted})
        conn.commit()
        result = {"status": "success", "topic": topic,
                  "profile_deleted": profile_deleted, "events_scanned": events_scanned,
                  "events_matched": events_matched, "events_deleted": events_deleted}

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
        # L2: audit.details at-rest sifreli -> decrypt (AAD = audit|details|agent|action|ts). Legacy seffaf.
        key_bytes = self._key()
        data = [
            {"id": r[0], "timestamp": r[1], "agent_id": r[2], "action": r[3],
             "details": json.loads(cell_crypt.decrypt_cell(r[4], key_bytes, cell_crypt.aad_audit(r[2], r[3], r[1]))),
             "entry_hash": r[5]}
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
        # L2: ham `content` audit'e YAZILMAZ -> digest (forget/unutulma-hakki ile tutarli).
        details = {"source": source, "type": type, "content": _digest(content), "ttl_days": ttl_days}

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
        # L2: content at-rest AES-GCM sifrelenir (AAD = events|content). Metadata (source/type/ttl) plaintext.
        enc_content = cell_crypt.encrypt_cell(json.dumps(content), self._key(), cell_crypt.aad_event())
        cursor.execute(
            "INSERT INTO events (timestamp, session_id, source, type, content, ttl_expiry) VALUES (?, ?, ?, ?, ?, ?)",
            (now, self.agent_id, source, type, enc_content, ttl_expiry)
        )
        event_id = cursor.lastrowid
        conn.commit()

        self.audit_chain.record(self.agent_id, action, {**details, "result": "success", "event_id": event_id})
        return {"status": "success", "event_id": event_id}
