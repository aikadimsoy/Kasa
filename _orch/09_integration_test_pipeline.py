"""
Integration test pipeline — tam sistem testi
deepseek taslak → qwen review → d:/kasa/tests/test_integration.py
"""
import json, re, os, py_compile, sys
import urllib.request

OLLAMA  = "http://localhost:11434/api/generate"
DRAFTER = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER= "qwen2.5-coder:14b"
ORCH    = "d:/kasa/_orch"

def call_model(model, prompt, label):
    print(f"\n[ORCH] {label} ({model})...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": 0.2, "num_predict": 4096}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
                                  headers={"Content-Type": "application/json"})
    buf = []
    with urllib.request.urlopen(req, timeout=300) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line: continue
            try:
                obj = json.loads(line)
                tok = obj.get("response","")
                buf.append(tok); print(tok, end="", flush=True)
                if obj.get("done"): break
            except: continue
    print(); return "".join(buf)

def save(name, content):
    os.makedirs(ORCH, exist_ok=True)
    path = f"{ORCH}/{name}"
    open(path, "w", encoding="utf-8").write(content)
    print(f"[ORCH] Kaydedildi: {path}")

def extract_python(text):
    m = re.search(r"```python\s*\r?\n(.*?)```", text, re.DOTALL)
    return m.group(1) if m else text

# ── ADIM 1: deepseek taslak ──
DRAFT_PROMPT = """
Write `tests/test_integration.py` for **Project KASA**.

## EXACT API — do not invent methods, use ONLY what is listed here

### Vault (src/vault/database.py)
```python
vault = Vault(vault_path="d:/kasa")   # takes vault_path string, NOT a db path
vault.connect()                        # connects + runs _init_schema() automatically
conn = vault.get_connection()          # returns sqlite3.Connection
vault.close()
# vault.db_path = os.path.join(vault_path, "kasa.db")
```

### AuditChain (src/vault/audit.py)
```python
chain = AuditChain(conn)               # conn is sqlite3.Connection
chain.record(agent_id, action, details_dict)  # returns entry_hash str
chain.verify_chain()                   # returns True if intact, False if tampered
```

### VaultTools (src/mcp_server/tools.py)
```python
tools = VaultTools(vault, agent_id="system")  # agent_id="system" bypasses permission checks
tools.event_ingest(source, event_type, content_dict, ttl_days=30)  # returns {"status":"success","event_id":int}
tools.profile_write(key, value, provenance)    # returns {"status":"success","key":str}
tools.profile_read(scope)                      # returns {"status":"success","count":int,"data":[...]}
tools.forget(topic)                            # returns {"status":"success","profile_deleted":int,...}
tools.audit_read(start_index=0, count=10)      # returns {"status":"success","count":int,"records":[...]}
```

## How to use a temp directory for isolation
```python
import tempfile, shutil
tmpdir = tempfile.mkdtemp()
vault = Vault(vault_path=tmpdir)
vault.connect()
# ... test ...
vault.close()
shutil.rmtree(tmpdir)
```

## Test structure (8 tests, use unittest.TestCase)

```python
import sys, os, sqlite3, tempfile, shutil, unittest
sys.path.insert(0, 'd:/kasa')
from src.vault.database import Vault
from src.vault.audit import AuditChain
from src.vault.schema import CREATE_AUDIT_TABLE
from src.mcp_server.tools import VaultTools

class TestVault(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.vault = Vault(vault_path=self.tmpdir)
        self.vault.connect()
        self.conn = self.vault.get_connection()

    def tearDown(self):
        self.vault.close()
        shutil.rmtree(self.tmpdir)

    def test_schema_created(self):
        # Check all 4 tables exist
        ...

    def test_write_and_read_event(self):
        # INSERT into events using raw SQL, SELECT back, check fields
        ...

class TestAuditChain(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(CREATE_AUDIT_TABLE)
        self.conn.commit()
        self.chain = AuditChain(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_record_and_verify(self):
        # record 3 entries, verify_chain() returns True
        ...

    def test_tamper_detected(self):
        # record 2, UPDATE audit SET action='tampered' WHERE id=1, verify returns False
        ...

class TestVaultTools(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.vault = Vault(vault_path=self.tmpdir)
        self.vault.connect()
        self.tools = VaultTools(self.vault, agent_id="system")

    def tearDown(self):
        self.vault.close()
        shutil.rmtree(self.tmpdir)

    def test_event_ingest(self): ...
    def test_profile_write_read(self): ...
    def test_forget(self): ...
    def test_audit_read(self): ...
```

Fill in all `...` with real test logic. Add Turkish docstrings.
Output ONLY the complete Python code inside a ```python ... ``` block.
""".strip()

draft_raw = call_model(DRAFTER, DRAFT_PROMPT, "TEST TASLAK")
save("09_test_draft_raw.txt", draft_raw)
draft_code = extract_python(draft_raw)
save("09_test_draft_code.py", draft_code)

# ── ADIM 2: qwen review ──
REVIEW_PROMPT = f"""
Review this `tests/test_integration.py` for Project KASA.

## Checklist
1. All 8 test cases present?
2. `:memory:` SQLite used (no file system writes)?
3. `sys.path.insert(0, 'd:/kasa')` at top?
4. `setUp` isolates each test?
5. `AuditChain` tamper test actually corrupts a row and expects False?
6. `event_ingest` test checks for `event_id` in result?
7. `forget` test verifies profile is empty after?
8. Any import errors or undefined names?
9. `if __name__ == '__main__': unittest.main()` present?

## Draft
```python
{draft_code[:7000]}
```

Output corrected complete ```python ... ``` block.
After: one-line Turkish summary.
""".strip()

review_raw = call_model(REVIEWER, REVIEW_PROMPT, "TEST REVIEW")
save("09_test_review_raw.txt", review_raw)
final_code = extract_python(review_raw)
save("09_test_final_code.py", final_code)

# ── ADIM 3: syntax check + uygula ──
tmp = f"{ORCH}/09_test_final_code.py"
try:
    py_compile.compile(tmp, doraise=True)
    print("[ORCH] py_compile: GECTI")
except py_compile.PyCompileError as e:
    print(f"[ORCH] HATA: {e}"); sys.exit(1)

os.makedirs("d:/kasa/tests", exist_ok=True)
init = "d:/kasa/tests/__init__.py"
if not os.path.exists(init):
    open(init, "w").write("")

out = "d:/kasa/tests/test_integration.py"
open(out, "w", encoding="utf-8").write(final_code)
print(f"\n[ORCH] {out} yazildi.")
print("[ORCH] Pipeline 09 tamamlandi.")
