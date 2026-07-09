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
    ttl_expiry REAL NOT NULL -- Timestamp when this event should be deleted
);
"""

CREATE_EVENTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
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

# Tüm DDL komutlarını bir listede topla
ALL_TABLES = [
    CREATE_EVENTS_TABLE,
    CREATE_PROFILE_TABLE,
    CREATE_PERMISSIONS_TABLE,
    CREATE_AUDIT_TABLE,
]

ALL_INDEXES = [
    CREATE_EVENTS_INDEX,
    CREATE_PROFILE_INDEX,
    CREATE_AUDIT_INDEX,
]
