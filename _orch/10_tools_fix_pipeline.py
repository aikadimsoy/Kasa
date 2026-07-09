"""
tools.py fix pipeline — 3 cerrahi düzeltme
qwen2.5-coder:14b tek geçişte düzeltir
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
        "options": {"temperature": 0.05, "num_predict": 5000}
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

current = open("d:/kasa/src/mcp_server/tools.py", encoding="utf-8").read()

FIX_PROMPT = f"""
Fix the following `src/mcp_server/tools.py` with exactly 3 surgical changes. Do NOT change anything else.

## Current file:
```python
{current}
```

## FIX 1 — event_ingest: wrong column names in INSERT (line ~227)
The `events` table schema is:
  `events(id INTEGER PK, timestamp REAL, session_id TEXT, source TEXT, type TEXT, content TEXT, ttl_expiry REAL)`
There is NO `created_at` column.

WRONG:
```python
cursor.execute(
    "INSERT INTO events (source, type, content, created_at, ttl_expiry) VALUES (?, ?, ?, ?, ?)",
    (source, type, json.dumps(content), now, ttl_expiry)
)
```

CORRECT:
```python
cursor.execute(
    "INSERT INTO events (timestamp, session_id, source, type, content, ttl_expiry) VALUES (?, ?, ?, ?, ?, ?)",
    (now, self.agent_id, source, type, json.dumps(content), ttl_expiry)
)
```

## FIX 2 — event_ingest: ttl_days must have a default value (line ~194)
WRONG: `def event_ingest(self, source: str, type: str, content: dict, ttl_days: int) -> dict:`
CORRECT: `def event_ingest(self, source: str, type: str, content: dict, ttl_days: int = 30) -> dict:`

## FIX 3 — audit_read: return key must be "records" not "data" (line ~189)
WRONG: `result = {{"status": "success", "count": len(data), "data": data}}`
CORRECT: `result = {{"status": "success", "count": len(data), "records": data}}`

Output the COMPLETE corrected file inside a ```python ... ``` block.
""".strip()

raw = call_model(REVIEWER, FIX_PROMPT, "TOOLS FIX")
fixed = extract_python(raw)

tmp = f"{ORCH}/10_tools_fixed.py"
open(tmp, "w", encoding="utf-8").write(fixed)
try:
    py_compile.compile(tmp, doraise=True)
    print("[ORCH] py_compile: GECTI")
except py_compile.PyCompileError as e:
    print(f"[ORCH] HATA: {e}"); sys.exit(1)

open("d:/kasa/src/mcp_server/tools.py", "w", encoding="utf-8").write(fixed)
print("\n[ORCH] src/mcp_server/tools.py guncellendi.")
print("[ORCH] Pipeline 10 tamamlandi.")
