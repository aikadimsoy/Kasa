# -*- coding: utf-8 -*-
"""L2 uctan-uca entegrasyon: sifreleme zinciri + at-rest plaintext yoklugu + forget + export."""
import sys, os, tempfile, json
sys.path.insert(0, "d:/kasa")
import pytest
from src.vault.database import Vault
from src.mcp_server.tools import VaultTools
from src.vault import cell_crypt as cc

def make_vault(tmp_path):
    v = Vault(vault_path=str(tmp_path / "vault")); v.connect()
    return v, VaultTools(v, "system")

@pytest.fixture(scope="function")
def vault_setup(tmp_path):
    v, t = make_vault(tmp_path)
    yield v, t
    v.close()

def test_forget_roundtrip_no_residue(vault_setup):
    v, t = vault_setup
    t.event_ingest("web", "note", {"m": "CANARY_X"}, ttl_days=5); r = t.forget("CANARY_X")
    assert r["events_matched"] >= 1 and r["events_deleted"] == r["events_matched"], r
    cur = v.get_connection().execute("SELECT id, content FROM events")
    resid = 0
    for row in cur.fetchall():
        try:
            p = cc.decrypt_cell(row["content"], v._db_key, cc.aad_event())
        except Exception:
            p = ""
        if "CANARY_X" in p:
            resid += 1
    assert resid == 0, f"forget sonrasi {resid} kalinti"

def test_forget_silent_zero_guard(vault_setup):
    v, t = vault_setup
    t.event_ingest("web", "note", {"CANARY_G2": ""}, ttl_days=5)
    class GuardCursor:
        def __init__(self, real): self._real = real; self._zero = False
        def execute(self, sql, params=()):
            if sql.lstrip().upper().startswith("DELETE FROM EVENTS"):
                self._zero = True; return self
            self._zero = False; self._real.execute(sql, params); return self
        def fetchall(self): return self._real.fetchall()
        def fetchone(self): return self._real.fetchone()
        @property
        def rowcount(self): return 0 if self._zero else self._real.rowcount
    class GuardConn:
        def __init__(self, real): self._real = real
        def cursor(self): return GuardCursor(self._real.cursor())
    t._db = lambda: GuardConn(v.get_connection())
    with pytest.raises(RuntimeError): t.forget("CANARY_G2")

def test_audit_chain_detects_ciphertext_tamper(vault_setup):
    v, t = vault_setup
    t.profile_write("user.preferences.seating", {"text": "aisle", "confidence": 0.9}, [1, 2])
    t.event_ingest("web", "note", {"secret_marker": "CANARY_AISLE_9931"}, ttl_days=10)
    assert v.audit_chain.verify_chain() is True, "verify_chain bozuk (encrypt-then-hash)"
    cur = v.get_connection().execute("SELECT id, details FROM audit ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    # Controller splice: details TEXT (str "K1:<base64>"); bytearray(str) TypeError, int!='A' hep True.
    # Son karakteri KESIN degistir (str uzerinde) -> stored hash mismatch -> verify_chain False.
    s = row["details"]
    flipped = s[:-1] + ("B" if s[-1] == "A" else "A")
    v.get_connection().execute("UPDATE audit SET details = ? WHERE id = ?", (flipped, row["id"]))
    v.get_connection().commit()
    assert not v.audit_chain.verify_chain(), "tamper edilen audit.details verify_chain'de YAKALANMADI"

def test_no_plaintext_leak_at_rest(vault_setup):
    v, t = vault_setup
    t.profile_write("user.profile.x", {"secret": "LEAK_MARKER_7"}, [1])
    v.close()
    with open(v.db_path, "rb") as f: raw_db = f.read()
    assert b"LEAK_MARKER_7" not in raw_db, "Plaintext leak detected in database"
    assert b"K1:" in raw_db, "Encrypted cell not found in database"

def test_aad_swap_breaks_decrypt(vault_setup):
    v, t = vault_setup
    t.profile_write("user.profile.a", {"text": "alpha_val_1"}, [1])
    t.profile_write("user.profile.b", {"text": "beta_val_2"}, [1])
    cur = v.get_connection().execute("SELECT key, value FROM profile")
    ciphertexts = dict(cur.fetchall())
    v.get_connection().execute("UPDATE profile SET value = ? WHERE key = ?", (ciphertexts["user.profile.b"], "user.profile.a"))
    v.get_connection().execute("UPDATE profile SET value = ? WHERE key = ?", (ciphertexts["user.profile.a"], "user.profile.b"))
    v.get_connection().commit()
    with pytest.raises(Exception): t.profile_read("user.profile.a")
