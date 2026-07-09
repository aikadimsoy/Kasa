"""
event_ingest pipeline — tools.py'a event_ingest metodu ekle
deepseek taslak → qwen review → d:/kasa/src/mcp_server/tools.py
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
                tok = obj.get("response", "")
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

# Mevcut tools.py içeriğini oku
current_tools = open("d:/kasa/src/mcp_server/tools.py", encoding="utf-8").read()

# ── ADIM 1: deepseek-coder taslak ──
DRAFT_PROMPT = f"""
You are an expert Python developer working on **Project KASA** — a local-first memory vault.

## Task
Add an `event_ingest` method to the existing `VaultTools` class in `src/mcp_server/tools.py`.

## Existing file (complete):
```python
{current_tools}
```

## What `event_ingest` must do:
1. Signature: `event_ingest(self, source: str, event_type: str, content: dict, ttl_days: int = 30) -> dict`
2. Permission check: scope `"events:write"` (deny-by-default, same pattern as other methods)
3. Validate inputs:
   - `source`: non-empty string, max 64 chars
   - `event_type`: non-empty string, max 64 chars
   - `content`: dict (JSON-serializable)
   - `ttl_days`: 1-365 integer
4. Insert into `events` table:
   - `timestamp` = `time.time()`
   - `session_id` = `self.agent_id` (reuse agent identity as session)
   - `source`, `type` = validated inputs
   - `content` = `json.dumps(content)`
   - `ttl_expiry` = `time.time() + ttl_days * 86400`
5. Audit: record `"event_ingest"` action with `{{source, type, ttl_days}}`
6. Return: `{{"status": "success", "event_id": <inserted rowid>}}`

## Rules:
- Parameterized SQL only (no f-string SQL)
- Turkish docstring
- Same error handling pattern as existing methods
- Output the COMPLETE updated `tools.py` inside a ```python ... ``` block.
""".strip()

draft_raw = call_model(DRAFTER, DRAFT_PROMPT, "EVENT_INGEST TASLAK")
save("08_event_ingest_draft_raw.txt", draft_raw)
draft_code = extract_python(draft_raw)
save("08_event_ingest_draft_code.py", draft_code)

# ── ADIM 2: qwen review ──
REVIEW_PROMPT = f"""
Review this updated `tools.py` for Project KASA.

## Checklist
1. `event_ingest` method present with correct signature?
2. Permission check with `events:write` scope?
3. Input validation (source/type max 64 chars, ttl_days 1-365)?
4. SQL parameterized (no f-string in INSERT)?
5. `ttl_expiry` = now + ttl_days * 86400?
6. Audit chain recorded?
7. Return dict has `status` and `event_id`?
8. All original methods (profile_read, profile_write, forget, audit_read) still intact?
9. Any import errors or undefined names?

## Draft Code
```python
{draft_code[:7000]}
```

Output the corrected complete ```python ... ``` block.
After: one-line Turkish summary of changes.
""".strip()

review_raw = call_model(REVIEWER, REVIEW_PROMPT, "EVENT_INGEST REVIEW")
save("08_event_ingest_review_raw.txt", review_raw)
final_code = extract_python(review_raw)
save("08_event_ingest_final_code.py", final_code)

# ── ADIM 3: syntax check + uygula ──
tmp = f"{ORCH}/08_event_ingest_final_code.py"
try:
    py_compile.compile(tmp, doraise=True)
    print("[ORCH] py_compile: GECTI")
except py_compile.PyCompileError as e:
    print(f"[ORCH] HATA: {e}"); sys.exit(1)

out = "d:/kasa/src/mcp_server/tools.py"
open(out, "w", encoding="utf-8").write(final_code)
print(f"\n[ORCH] {out} yazildi.")
print("[ORCH] Pipeline 08 tamamlandi.")
