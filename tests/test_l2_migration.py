# -*- coding: utf-8 -*-
"""
L2 migration KALICI regresyon (Controller). Yakalanan false-PASS: migration mantiksal olarak
"basarili" (verify_chain OK, tum satirlar sifreli) gorunse bile, SQLite UPDATE eski plaintext'i
serbest sayfalarda BIRAKIR -> ham DB dosyasinda kalinti sizinti. VACUUM + secure_delete bunu kapatir.
Bu test o kalinti-sizintiyi surekli avlar; ayrica idempotency + zincir-yeniden-kurulumunu dogrular.
"""
import sys
import os
import time
import tempfile

sys.path.insert(0, "d:/kasa")
from src.vault.database import Vault
from src.vault.audit import AuditChain
from src.vault import cell_crypt
from tools.migrate_l2_encrypt import migrate

LINGER = "LINGER_MARKER_42"
PROFVAL = "PROFVAL_88"


def _make_legacy_vault(tmp):
    """DOGRUDAN INSERT ile (sifreleme bypass) legacy DUZ METIN vault kurar + plaintext audit zinciri."""
    v = Vault(vault_path=tmp)
    v.connect()
    conn = v.get_connection()
    conn.execute(
        "INSERT INTO events (timestamp, session_id, source, type, content, ttl_expiry) VALUES (?,?,?,?,?,?)",
        (time.time(), "s", "web", "note", '{"m":"%s"}' % LINGER, time.time() + 3600))
    conn.execute(
        "INSERT INTO profile (key, value, provenance, created_at, updated_at) VALUES (?,?,?,?,?)",
        ("user.profile.x", '{"v":"%s"}' % PROFVAL, "[1]", time.time(), time.time()))
    conn.commit()
    ac = AuditChain(conn, key=None)  # key=None -> plaintext details, gecerli zincir
    ac.record("system", "legacy_a", {"x": 1})
    ac.record("system", "legacy_b", {"y": 2})
    v.close()


def test_migration_purges_lingering_plaintext_and_verifies():
    tmp = tempfile.mkdtemp()
    _make_legacy_vault(tmp)
    db = os.path.join(tmp, "kasa.db")

    # once: plaintext ham DB'de VAR
    assert LINGER.encode() in open(db, "rb").read()

    stats = migrate(tmp, dry_run=False)
    assert stats["events_enc"] >= 1 and stats["profile_enc"] >= 1 and stats["audit_enc"] >= 1

    raw = open(db, "rb").read()
    # KRITIK: VACUUM sonrasi hicbir kalinti plaintext kalmamali
    assert LINGER.encode() not in raw, "migration-kalinti sizinti: events plaintext ham DB'de"
    assert PROFVAL.encode() not in raw, "migration-kalinti sizinti: profile plaintext ham DB'de"
    assert b"K1:" in raw

    # verify: zincir yeniden kuruldu + degerler dogru cozuluyor
    v = Vault(vault_path=tmp)
    v.connect()
    try:
        assert v.audit_chain.verify_chain() is True
        conn = v.get_connection()
        row = conn.execute("SELECT key, value FROM profile WHERE key='user.profile.x'").fetchone()
        dec = cell_crypt.decrypt_cell(row["value"], v._db_key, cell_crypt.aad_profile("user.profile.x"))
        assert PROFVAL in dec
    finally:
        v.close()


def test_migration_is_idempotent():
    tmp = tempfile.mkdtemp()
    _make_legacy_vault(tmp)
    migrate(tmp, dry_run=False)              # 1. tur: hepsi sifrelenir
    stats2 = migrate(tmp, dry_run=False)     # 2. tur: hepsi zaten K1: -> atlanmali
    assert stats2["events_enc"] == 0 and stats2["profile_enc"] == 0
    assert stats2["events_skip"] >= 1 and stats2["profile_skip"] >= 1 and stats2["audit_skip"] >= 1

    # cifte-migration sonrasi hala verify + decrypt saglam
    v = Vault(vault_path=tmp)
    v.connect()
    try:
        assert v.audit_chain.verify_chain() is True
    finally:
        v.close()
