# kasa/src/vault/database.py

"""
SQLite veritabanı bağlantısını ve temel operasyonları yöneten Vault sınıfı.
Bu sınıf, SQLCipher yerine dosya tabanlı şifreleme için DPAPI kullanır.
Veritabanı dosyası şifrelenmez, ancak veritabanını açmak için gereken
anahtar şifrelenir. Bu, SQLCipher'ın Windows'taki derleme zorluklarını aşar.
"""

import sqlite3
import os
import hashlib
import time
from . import schema
from . import encryption
from .audit import AuditChain

# Anahtarın saklanacağı dosya adı
KEY_FILE_NAME = ".vaultkey"

class Vault:
    def __init__(self, vault_path: str, vault_password: str = None):
        """
        Kasa'yı başlatır.

        Args:
            vault_path: Kasa veritabanı dosyasının yolu.
            vault_password: (Opsiyonel) Ek bir parola. Belirtilirse, DPAPI anahtarı
                            bu parolayla birleştirilerek daha güçlü hale getirilir.
        """
        self.vault_path = vault_path
        os.makedirs(vault_path, exist_ok=True)
        self.db_path = os.path.join(vault_path, "kasa.db")
        self.key_path = os.path.join(vault_path, KEY_FILE_NAME)
        self._password = vault_password
        self._db_key = self._get_or_create_db_key()
        
        self.conn = None
        self.audit_chain = None

    def _get_or_create_db_key(self) -> bytes:
        """
        Veritabanı anahtarını DPAPI ile korunan dosyadan okur veya oluşturur.
        """
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                encrypted_key = f.read()
            db_key = encryption.unprotect_data(encrypted_key)
        else:
            # 32 byte (256-bit) rastgele anahtar oluştur
            db_key = os.urandom(32)
            encrypted_key = encryption.protect_data(db_key)
            with open(self.key_path, "wb") as f:
                f.write(encrypted_key)
        
        # Eğer ek parola varsa, anahtarı zenginleştir
        if self._password:
            return hashlib.sha256(db_key + self._password.encode('utf-8')).digest()
        
        return db_key

    def connect(self):
        """Veritabanına bağlanır ve şemayı oluşturur."""
        if self.conn:
            return

        # pysqlcipher3 yerine standart sqlite3 ve pragma key kullanıyoruz.
        # Bu, SQLCipher'ın sisteme kurulmuş olmasını gerektirir.
        # Daha basit bir yaklaşım için, bu satırı normal sqlite3 bağlantısıyla değiştirebiliriz.
        # Şimdilik, SQLCipher'ın olmadığını varsayarak ilerleyelim.
        # Veritabanı şifrelemesi şimdilik atlanmıştır. Anahtar yönetimi DPAPI ile yapılıyor.
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA secure_delete=ON")

        self._init_schema()
        self.audit_chain = AuditChain(self.conn)

    def _init_schema(self):
        """Veritabanı şemasını ve indekslerini oluşturur."""
        cursor = self.conn.cursor()
        for table_sql in schema.ALL_TABLES:
            cursor.execute(table_sql)
        for index_sql in schema.ALL_INDEXES:
            cursor.execute(index_sql)
        self.conn.commit()
        # Mevcut DB'ler için idempotent migration
        for migration in (
            "ALTER TABLE profile ADD COLUMN supersedes INTEGER",
            "ALTER TABLE events ADD COLUMN distilled INTEGER DEFAULT 0",
        ):
            try:
                self.conn.execute(migration)
                self.conn.commit()
            except Exception:
                pass  # Sütun zaten var

    def close(self):
        """Veritabanı bağlantısını kapatır."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_connection(self):
        """Ham veritabanı bağlantısını döndürür."""
        if not self.conn:
            self.connect()
        return self.conn

if __name__ == '__main__':
    # Test kodu
    test_vault_dir = "test_vault"
    if not os.path.exists(test_vault_dir):
        os.makedirs(test_vault_dir)

    print("Kasa oluşturuluyor ve bağlanılıyor...")
    with Vault(test_vault_dir) as vault:
        conn = vault.get_connection()
        cursor = conn.cursor()
        
        # Test verisi ekle
        ts = time.time()
        cursor.execute(
            "INSERT INTO events (timestamp, session_id, source, type, content, ttl_expiry) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, "test_session_123", "test_script", "test_event", '{"data": "hello"}', ts + 86400)
        )
        conn.commit()
        
        # Veriyi oku
        cursor.execute("SELECT * FROM events")
        row = cursor.fetchone()
        print("\nOkunan test verisi:")
        print(dict(row))
        assert row['session_id'] == "test_session_123"

    print("\nTest başarılı. Kasa veritabanı ve anahtar dosyası 'test_vault' klasöründe oluşturuldu.")
    # Cleanup
    # import shutil
    # shutil.rmtree(test_vault_dir)
