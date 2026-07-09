# kasa/src/vault/audit.py

"""
Değişmez, hash-zincirli denetim (audit) kaydı mekanizması.
Her yeni kayıt, bir önceki kaydın hash'ini içerir, bu da
aradan kayıt silmeyi veya değiştirmeyi tespit edilebilir kılar.
"""

import sqlite3
import hashlib
import time
import json

class AuditChain:
    def __init__(self, connection: sqlite3.Connection):
        """
        AuditChain'i başlatır.

        Args:
            connection: Aktif veritabanı bağlantısı.
        """
        self.conn = connection

    def _get_last_hash(self) -> str:
        """Veritabanındaki son denetim kaydının hash'ini alır."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT entry_hash FROM audit ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            # "Genesis block" hash'i
            return hashlib.sha256(b"genesis").hexdigest()

    def record(self, agent_id: str, action: str, details: dict = None) -> str:
        """
        Denetim zincirine yeni bir kayıt ekler.

        Args:
            agent_id: İşlemi yapan ajanın kimliği.
            action: Yapılan işlemin adı (örn: 'profile_read').
            details: İşlemle ilgili ek detayları içeren bir sözlük.

        Returns:
            Oluşturulan yeni denetim kaydının hash'i.
        """
        timestamp = time.time()
        details_json = json.dumps(details) if details else "{}"
        previous_hash = self._get_last_hash()

        # Yeni kaydın hash'ini hesapla
        hasher = hashlib.sha256()
        hasher.update(str(timestamp).encode('utf-8'))
        hasher.update(agent_id.encode('utf-8'))
        hasher.update(action.encode('utf-8'))
        hasher.update(details_json.encode('utf-8'))
        hasher.update(previous_hash.encode('utf-8'))
        entry_hash = hasher.hexdigest()

        # Veritabanına kaydet
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO audit (timestamp, agent_id, action, details, previous_hash, entry_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (timestamp, agent_id, action, details_json, previous_hash, entry_hash)
        )
        self.conn.commit()

        return entry_hash

    def verify_chain(self) -> bool:
        """
        Tüm denetim zincirinin bütünlüğünü doğrular.

        Returns:
            Zincir geçerliyse True, değilse False.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, timestamp, agent_id, action, details, previous_hash, entry_hash FROM audit ORDER BY id ASC")
        
        last_hash = hashlib.sha256(b"genesis").hexdigest()
        
        for row in cursor.fetchall():
            # Beklenen previous_hash'i kontrol et
            if row['previous_hash'] != last_hash:
                print(f"Hata: Kayıt {row['id']} için hash zinciri bozuk! Beklenen: {last_hash}, Gelen: {row['previous_hash']}")
                return False

            # Mevcut kaydın hash'ini yeniden hesapla ve doğrula
            hasher = hashlib.sha256()
            hasher.update(str(row['timestamp']).encode('utf-8'))
            hasher.update(row['agent_id'].encode('utf-8'))
            hasher.update(row['action'].encode('utf-8'))
            hasher.update(row['details'].encode('utf-8'))
            hasher.update(row['previous_hash'].encode('utf-8'))
            recalculated_hash = hasher.hexdigest()

            if recalculated_hash != row['entry_hash']:
                print(f"Hata: Kayıt {row['id']} için içerik değiştirilmiş! Hash uyuşmazlığı.")
                return False
            
            last_hash = recalculated_hash
            
        return True

if __name__ == '__main__':
    # Test kodu
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    # Şemayı oluştur
    from . import schema
    cursor = conn.cursor()
    cursor.execute(schema.CREATE_AUDIT_TABLE)
    conn.commit()

    audit_chain = AuditChain(conn)

    print("Denetim kayıtları oluşturuluyor...")
    audit_chain.record("copilot", "vault_init", {"status": "success"})
    time.sleep(0.1)
    audit_chain.record("user", "profile_read", {"scope": "user_preferences.seating"})
    time.sleep(0.1)
    audit_chain.record("distill_agent", "profile_write", {"key": "user_preferences.seating", "value": "aisle"})

    print("\nDenetim zinciri doğrulanıyor...")
    is_valid = audit_chain.verify_chain()
    print(f"Zincir geçerli mi? -> {is_valid}")
    assert is_valid

    # Zinciri bozmayı dene
    print("\nZincir bozuluyor (test amaçlı)...")
    cursor.execute("UPDATE audit SET action = 'tampered' WHERE id = 2")
    conn.commit()

    print("Bozuk zincir doğrulanıyor...")
    is_valid_after_tamper = audit_chain.verify_chain()
    print(f"Bozuk zincir geçerli mi? -> {is_valid_after_tamper}")
    assert not is_valid_after_tamper

    print("\nAuditChain testi başarıyla tamamlandı.")
    conn.close()
