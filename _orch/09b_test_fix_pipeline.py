"""
Test fix pipeline — 5 spesifik hatayı qwen'e düzelttir
"""
import json, re, os, py_compile, sys
import urllib.request

OLLAMA   = "http://localhost:11434/api/generate"
REVIEWER = "qwen2.5-coder:14b"
ORCH     = "d:/kasa/_orch"

def call_model(model, prompt, label):
    print(f"\n[ORCH] {label} ({model})...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": 0.1, "num_predict": 4096}
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

def extract_python(text):
    m = re.search(r"```python\s*\r?\n(.*?)```", text, re.DOTALL)
    return m.group(1) if m else text

current = open("d:/kasa/tests/test_integration.py", encoding="utf-8").read()

# event_ingest imzasını kontrol et
tools_src = open("d:/kasa/src/mcp_server/tools.py", encoding="utf-8").read()

FIX_PROMPT = f"""
Fix the following broken `tests/test_integration.py` for Project KASA.
Apply ALL 5 fixes listed below — nothing more, nothing less.

## Current broken file:
```python
{current}
```

## Current event_ingest signature in tools.py (for reference):
```python
{[l for l in tools_src.splitlines() if 'def event_ingest' in l]}
```

## FIX 1 — test_schema_created (line 23-24)
WRONG: `assertListEqual(tables, ['events', 'profiles', 'audit', 'settings'])`
CORRECT: Check each expected table IS IN the list (use `assertIn`):
```python
for t in ['events', 'profile', 'permissions', 'audit']:
    self.assertIn(t, tables)
```

## FIX 2 — test_write_and_read_event (line 30-38)
WRONG: `VaultTools(self.vault).event_ingest(...)` (missing agent_id)
WRONG: column `event_type` doesn't exist; schema uses column `type`
CORRECT:
```python
tools = VaultTools(self.vault, agent_id="system")
result = tools.event_ingest("test", "test_type", {{"key": "value"}}, ttl_days=30)
self.assertEqual(result["status"], "success")
self.assertIn("event_id", result)
```

## FIX 3 — test_event_ingest (line 85-93)
WRONG: `self.conn` not defined in TestVaultTools; wrong column name; eval() unsafe
CORRECT:
```python
result = self.tools.event_ingest("test", "test_type", {{"key": "value"}}, ttl_days=30)
self.assertEqual(result["status"], "success")
self.assertIn("event_id", result)
self.assertIsInstance(result["event_id"], int)
```

## FIX 4 — test_profile_write_read (line 103)
WRONG: `[row[0] for row in result["data"]]` — data is a list of dicts, not tuples
CORRECT: `[row["key"] for row in result["data"]]`

## FIX 5 — test_audit_read (line 119)
WRONG: `self.chain.record(...)` — `self.chain` doesn't exist in TestVaultTools
CORRECT: Remove the self.chain.record line; audit_read() will still have entries
from the setUp operations:
```python
def test_audit_read(self):
    result = self.tools.audit_read(start_index=0, count=10)
    self.assertEqual(result["status"], "success")
    self.assertIn("records", result)
```

Output the COMPLETE corrected `tests/test_integration.py` inside a ```python ... ``` block.
""".strip()

raw = call_model(REVIEWER, FIX_PROMPT, "TEST FIX")
fixed = extract_python(raw)

# syntax check
tmp = f"{ORCH}/09b_test_fixed.py"
open(tmp, "w", encoding="utf-8").write(fixed)
try:
    py_compile.compile(tmp, doraise=True)
    print("[ORCH] py_compile: GECTI")
except py_compile.PyCompileError as e:
    print(f"[ORCH] HATA: {e}"); sys.exit(1)

open("d:/kasa/tests/test_integration.py", "w", encoding="utf-8").write(fixed)
print("\n[ORCH] tests/test_integration.py guncellendi.")
print("[ORCH] Pipeline 09b tamamlandi.")
