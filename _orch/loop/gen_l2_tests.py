# -*- coding: utf-8 -*-
"""
gen_l2_tests — L2 at-rest kalici regresyon testlerini (T1-T5) YEREL modellere yazdirir.
SIFIR-TOKEN: deepseek taslak -> qwen inceleme -> pytest; FAIL ise pytest ciktisiyla
qwen fix turu (en fazla 3). Claude yalniz bu pipeline'i surer, test kodu yazmaz.
Kullanim: python d:/kasa/_orch/loop/gen_l2_tests.py
"""
import os
import sys, sys, time, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_pipe import call_model, extract_python, ollama_up, DRAFTER, REVIEWER

# Turkce not: depo koku dosya konumundan turetilir (sabit "d:/kasa" tasinabilir degildi).
KASA = os.environ.get("KASA_ROOT") or os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(KASA, "tests", "test_l2_at_rest.py")
# Turkce not: referans, URETIM aninda kullanilan GECICI bir calisma dosyasiydi; sabit yol
# hem tasinabilir degildi hem oturum kimligi siziyordu -> disaridan KASA_L2_REF ile verilir.
REF_PATH = os.environ.get("KASA_L2_REF", "")
MAX_FIX_ROUNDS = 3

with open(REF_PATH, encoding="utf-8") as f:
    REF = f.read()

# --- SPEC (yerel modele giden is tanimi; prompt dili Ingilizce — pipeline kurali) ---
SPEC = f"""You are writing a pytest regression test file for the KASA project (Windows, Python 3.14).
Write the COMPLETE file `tests/test_l2_at_rest.py` containing EXACTLY five tests T1-T5 that
permanently prove the L2 at-rest encryption does not regress into false-PASS.

=== GROUND TRUTH: a WORKING integration script (this API is verified, use ONLY this API) ===
```python
{REF}
```

=== ADDITIONAL VERIFIED FACTS (do not invent anything beyond these) ===
- `Vault(vault_path=dir)` creates `dir` (makedirs exist_ok) and sets `v.db_path = dir/kasa.db`.
  `v.connect()`, `v.close()`, `v.get_connection()` (sqlite3, row_factory=sqlite3.Row),
  `v._db_key` (bytes), `v.audit_chain.verify_chain() -> bool`.
- `VaultTools(v, "system")` bypasses permissions. `t._db()` returns the sqlite3 connection
  used internally by tools (forget() calls `conn = self._db(); cursor = conn.cursor()`).
- Tables: `events(id, timestamp, session_id, source, type, content, ttl_expiry, distilled)`
  with `content` an encrypted cell string starting with "K1:";
  `profile(id, key TEXT plaintext UNIQUE, value TEXT encrypted, provenance, updated_at)`;
  `audit(id, timestamp, agent_id, action, details TEXT encrypted-then-hashed, ...)`.
- `forget(topic)` internals (relevant excerpt, real code):
```
conn = self._db()
cursor = conn.cursor()
cursor.execute("DELETE FROM profile WHERE key LIKE ?", (topic + '%',))
...
cursor.execute("SELECT id, content FROM events")
rows = cursor.fetchall()
... decrypt each row, collect match_ids ...
cursor.execute(f"DELETE FROM events WHERE id IN (...)", match_ids)
events_deleted = cursor.rowcount
if events_matched != events_deleted:
    raise RuntimeError(...)
```
- `cell_crypt.decrypt_cell(cell, key, aad)` raises (InvalidTag) on wrong AAD/ciphertext;
  `cc.aad_event()` for events.content, `cc.aad_profile(key)` for profile.value.
- `profile_read` decrypts each row with `aad_profile(row_key)` and does NOT swallow
  decryption exceptions.

=== THE FIVE TESTS ===
Each test builds its OWN isolated vault. Use a small helper:
```
def make_vault(tmp_path):
    v = Vault(vault_path=str(tmp_path / "vault")); v.connect()
    return v, VaultTools(v, "system")
```
(use pytest's built-in `tmp_path` fixture; close the vault with try/except at test end where needed).

T1 test_forget_roundtrip_no_residue:
  event_ingest("web", "note", {{"m": "CANARY_X"}}, ttl_days=5); r = forget("CANARY_X").
  ASSERT r["events_matched"] >= 1 AND r["events_deleted"] == r["events_matched"].
  Then decrypt-scan ALL remaining events rows (SELECT id, content FROM events; decrypt_cell
  with v._db_key and cc.aad_event(); on exception treat as ""); ASSERT zero rows containing
  "CANARY_X".

T2 test_forget_silent_zero_guard:
  event_ingest a "CANARY_G2" event. Then monkeypatch `t._db` (instance attribute:
  `t._db = lambda: GuardConn(v.get_connection())`) with delegating wrapper classes so that
  ONLY SQL starting with "DELETE FROM events" is NOT executed and reports rowcount 0:
```
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
    def __getattr__(self, name): return getattr(self._real, name)

class GuardConn:
    def __init__(self, real): self._real = real
    def cursor(self): return GuardCursor(self._real.cursor())
    def __getattr__(self, name): return getattr(self._real, name)
```
  ASSERT with pytest.raises(RuntimeError): t.forget("CANARY_G2").

T3 test_audit_chain_detects_ciphertext_tamper:
  Do a profile_write and an event_ingest (audit fills). ASSERT v.audit_chain.verify_chain()
  is True. Then fetch the LAST audit row: SELECT id, details FROM audit ORDER BY id DESC
  LIMIT 1; corrupt exactly one byte: new_last = 'A' if details[-1] != 'A' else 'B';
  UPDATE audit SET details = corrupted WHERE id = ?; commit.
  ASSERT verify_chain() is False.

T4 test_no_plaintext_leak_at_rest:
  profile_write("user.profile.x", {{"secret": "LEAK_MARKER_7"}}, [1]); v.close().
  Read raw bytes of v.db_path and, if they exist, v.db_path + "-wal", "-shm", "-journal".
  ASSERT b"LEAK_MARKER_7" not in any of them; ASSERT b"K1:" IS in the main db bytes.

T5 test_aad_swap_breaks_decrypt:
  profile_write("user.profile.a", {{"text": "alpha_val_1"}}, [1]) and
  profile_write("user.profile.b", {{"text": "beta_val_2"}}, [1]).
  Read both ciphertexts (SELECT key, value FROM profile), SWAP them with two
  UPDATE profile SET value=? WHERE key=? statements, commit.
  ASSERT with pytest.raises(Exception): t.profile_read("user.profile.a")
  (wrong AAD -> InvalidTag).

=== HARD REQUIREMENTS ===
- File starts with: `# -*- coding: utf-8 -*-`, then imports:
  `import sys; sys.path.insert(0, "d:/kasa")` BEFORE the src imports.
  `import pytest`, `from src.vault.database import Vault`,
  `from src.mcp_server.tools import VaultTools`, `from src.vault import cell_crypt as cc`.
- Use ONLY the API shown above. NO made-up methods, NO mocks beyond the T2 wrappers.
- Comments in Turkish (ASCII ok), code identifiers in English.
- Output the COMPLETE file in ONE ```python``` block. No prose outside the block.
"""

CHECKLIST = """- [ ] Exactly 5 tests named test_forget_roundtrip_no_residue, test_forget_silent_zero_guard,
      test_audit_chain_detects_ciphertext_tamper, test_no_plaintext_leak_at_rest,
      test_aad_swap_breaks_decrypt; each builds its own vault via make_vault(tmp_path).
- [ ] sys.path.insert(0, "d:/kasa") happens BEFORE `from src...` imports; `import pytest` present.
- [ ] T1: asserts events_matched >= 1, events_deleted == events_matched, AND decrypt-scans
      remaining events proving zero "CANARY_X" residue (residue count assert == 0).
- [ ] T2: pytest.raises(RuntimeError) around t.forget(...); wrapper intercepts ONLY
      "DELETE FROM events" SQL (DELETE FROM profile must still execute for real);
      rowcount is a property returning 0 only for the intercepted statement.
- [ ] T3: verify_chain() True asserted BEFORE tamper, False asserted AFTER a one-character
      change to the last audit row's details, with conn.commit() after the UPDATE.
- [ ] T4: v.close() BEFORE reading files; checks -wal/-shm/-journal siblings when present;
      asserts b"LEAK_MARKER_7" absent everywhere AND b"K1:" present in kasa.db bytes.
- [ ] T5: two profile_write calls with DIFFERENT keys, ciphertext values swapped via SQL
      UPDATE + commit, then pytest.raises(Exception) around profile_read.
- [ ] No invented API: only Vault, VaultTools, cell_crypt functions, v._db_key, v.db_path,
      v.get_connection(), v.audit_chain.verify_chain(), t._db monkeypatching as specified.
- [ ] Tests really bite: no bare `assert True`, no try/except swallowing the asserted error.
- [ ] Valid Python: file parses; one complete ```python``` block only.
"""


def run_pytest():
    """Uretilen dosyayi kosar; (ok, cikti) doner."""
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_l2_at_rest.py", "-q",
                        "--no-header", "-x"],
                       cwd=KASA, capture_output=True, text=True, timeout=600)
    out = (p.stdout or "") + "\n" + (p.stderr or "")
    return p.returncode == 0, out


def write_out(code):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(code)


def main():
    if not ollama_up():
        print("FATAL: ollama ayakta degil"); sys.exit(2)
    timings = []

    # Tur 1: deepseek taslak
    t0 = time.time()
    draft = call_model(DRAFTER, SPEC, num_predict=4096)
    timings.append(("deepseek-draft", time.time() - t0))
    code = extract_python(draft)

    # Tur 1b: qwen inceleme
    t0 = time.time()
    review_prompt = ("Review and FIX the draft against the checklist. Keep the five tests and the "
                     "verified API exactly as specified. Output ONLY the complete corrected file "
                     "in one ```python``` block.\n\n=== SPEC (authoritative) ===\n" + SPEC +
                     "\n\n=== CHECKLIST ===\n" + CHECKLIST +
                     "\n\n=== DRAFT ===\n```python\n" + code[:13000] + "\n```")
    review = call_model(REVIEWER, review_prompt, num_predict=4096)
    timings.append(("qwen-review", time.time() - t0))
    code = extract_python(review)
    write_out(code)

    ok, out = run_pytest()
    rnd = 0
    while not ok and rnd < MAX_FIX_ROUNDS:
        rnd += 1
        print(f"--- pytest FAIL, qwen fix turu {rnd} ---\n{out[-3000:]}")
        t0 = time.time()
        fix_prompt = ("The pytest file below FAILS. Fix it. Use ONLY the verified API from the "
                      "spec. Do NOT weaken any assertion; fix the mechanics instead. Output ONLY "
                      "the complete corrected file in one ```python``` block.\n\n"
                      "=== SPEC (authoritative) ===\n" + SPEC +
                      "\n\n=== CHECKLIST ===\n" + CHECKLIST +
                      "\n\n=== PYTEST OUTPUT ===\n" + out[-4000:] +
                      "\n\n=== CURRENT FILE ===\n```python\n" + code[:13000] + "\n```")
        fixed = call_model(REVIEWER, fix_prompt, num_predict=4096)
        timings.append((f"qwen-fix-{rnd}", time.time() - t0))
        code = extract_python(fixed)
        write_out(code)
        ok, out = run_pytest()

    print("=== TIMINGS ===")
    for name, dt in timings:
        print(f"{name}: {dt:.1f}s")
    print("=== PYTEST ===")
    print(out)
    print("SONUC:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
