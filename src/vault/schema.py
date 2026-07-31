# kasa/src/vault/schema.py

"""
Veritabanı şemasını (DDL - Data Definition Language) tanımlar.
Bu script doğrudan çalıştırılmaz, database.py tarafından kullanılır.
"""

# Olaylar (Events): Ham etkileşim kayıtları, kısa süreli (TTL).
CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    session_id TEXT NOT NULL,
    source TEXT NOT NULL, -- e.g., 'browser_extension', 'manual_entry'
    type TEXT NOT NULL, -- e.g., 'page_view', 'form_submit'
    content TEXT NOT NULL, -- JSON blob of event data
    ttl_expiry REAL NOT NULL, -- Timestamp when this event should be deleted
    content_hash TEXT, -- HMAC-SHA256(vault-key, source|type|content): dedup kimligi (DEBI-1)
    occurrence_count INTEGER NOT NULL DEFAULT 1, -- ayni olayin kac kez gozlendigi
    last_seen REAL -- son tekrarin zamani (ilk kayitta = timestamp)
);
"""

CREATE_EVENTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
"""

# DEBI-1 dedup arama indeksi. ALL_INDEXES'e EKLENMEZ: eski DB'lerde content_hash kolonu
# ALTER-migration ile gelir; indeks migration SONRASI database._init_schema'da kurulur.
CREATE_EVENTS_HASH_INDEX = """
CREATE INDEX IF NOT EXISTS idx_events_content_hash ON events (content_hash);
"""

# Profil (Profile): Damıtılmış, kalıcı, insan tarafından okunabilir bilgiler.
CREATE_PROFILE_TABLE = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    provenance TEXT NOT NULL, -- JSON array of event IDs
    supersedes INTEGER,       -- önceki versiyonun satır ID'si
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""

CREATE_PROFILE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_profile_key ON profile (key);
"""

# İzinler (Permissions): Ajanların hangi kapsamlara erişebileceğini belirler.
CREATE_PERMISSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL, -- The unique identifier for the agent/client
    scope TEXT NOT NULL, -- e.g., 'profile:read:all', 'events:read'
    granted_at REAL NOT NULL,
    revoked_at REAL,
    UNIQUE(agent_id, scope)
);
"""

# Denetim (Audit): Tüm sistem erişim ve değişikliklerinin değişmez kaydı.
CREATE_AUDIT_TABLE = """
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    agent_id TEXT NOT NULL,
    action TEXT NOT NULL, -- e.g., 'profile_read', 'forget'
    details TEXT, -- JSON blob with action parameters and result summary
    previous_hash TEXT NOT NULL, -- SHA-256 of the previous audit entry
    entry_hash TEXT UNIQUE NOT NULL -- SHA-256 of this entry (timestamp + ... + previous_hash)
);
"""

CREATE_AUDIT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit (timestamp);
"""

# Denetim kontrol noktalari (DEBI-2): zincirin donemsel kapanis muhurleri.
# Sebep: audit zinciri yalnizca uca ekler, aradan silinemez -> sinirsiz buyur.
# Checkpoint son entry_hash'i ayri tabloya sabitler; ondan eski kayitlar arsivlenebilir,
# verify_chain genesis yerine muhurden tohumlanir (T7 garantisi bozulmaz).
CREATE_AUDIT_CHECKPOINT_TABLE = """
CREATE TABLE IF NOT EXISTS audit_checkpoint (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    upto_id INTEGER NOT NULL, -- muhurlenen son audit satirinin id'si
    upto_hash TEXT NOT NULL, -- muhurlenen son audit satirinin entry_hash'i
    entry_count INTEGER NOT NULL -- muhur anindaki kapsanan kayit sayisi
);
"""

# Tüm DDL komutlarını bir listede topla
ALL_TABLES = [
    CREATE_EVENTS_TABLE,
    CREATE_PROFILE_TABLE,
    CREATE_PERMISSIONS_TABLE,
    CREATE_AUDIT_TABLE,
    CREATE_AUDIT_CHECKPOINT_TABLE,
]

ALL_INDEXES = [
    CREATE_EVENTS_INDEX,
    CREATE_PROFILE_INDEX,
    CREATE_AUDIT_INDEX,
]
