"""
KASA Orkestrasyon Pipeline'i
Kural: deepseek-coder-v2:16b taslak → qwen2.5-coder:14b review → uygula
"""
import json, sys, textwrap, time
import urllib.request

OLLAMA = "http://localhost:11434/api/generate"
DRAFTER = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
ORCH_DIR = "d:/kasa/_orch"

def call_model(model: str, prompt: str, label: str) -> str:
    print(f"\n[ORCH] {label} ({model}) cagiriliyor...", flush=True)
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.2, "num_predict": 4096}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
                                  headers={"Content-Type": "application/json"})
    result = []
    with urllib.request.urlopen(req, timeout=300) as resp:
        for raw_line in resp:
            line = raw_line.decode().strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                token = obj.get("response", "")
                result.append(token)
                print(token, end="", flush=True)
                if obj.get("done"):
                    break
            except json.JSONDecodeError:
                continue
    print()
    return "".join(result)

def save(filename: str, content: str):
    import os
    os.makedirs(ORCH_DIR, exist_ok=True)
    path = f"{ORCH_DIR}/{filename}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[ORCH] Kaydedildi: {path}")

def extract_python(text: str) -> str:
    """Cevaptan ilk ```python ... ``` bloğunu çıkarır."""
    import re
    m = re.search(r"```python\s*\r?\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1)
    # Kod bloğu işaretsizse ham dön
    return text

# ── ADIM 1: deepseek-coder taslak ──────────────────────────────────────────
DRAFT_PROMPT = textwrap.dedent("""
You are an expert Python developer. Write the complete Python module
`src/distill/engine.py` for **Project KASA** — a local-first, encrypted
memory vault for agentic browsing on Windows.

## Context
- The vault uses SQLite (sqlite3 stdlib) at `d:/kasa/kasa.db`.
- Tables already exist: `events(id, timestamp, session_id, source, type, content TEXT JSON, ttl_expiry)`,
  `profile(id, key TEXT UNIQUE, value TEXT JSON, provenance TEXT JSON, created_at, updated_at)`.
- Local LLM inference is via Ollama HTTP API at `http://localhost:11434/api/generate`.
  Model to use: `qwen2.5:7b`.
- The distillation principle: Store(D) ≈ H(D|M) — only store facts not already
  derivable from the model; keep them human-readable.

## What the module must do
1. `DistillEngine(db_path, ollama_url)` class.
2. `run_batch(max_events=100)` method:
   a. Reads up to `max_events` unexpired events from `events` table where
      `ttl_expiry > now()` and that have NOT yet been distilled
      (use a `distilled` INTEGER DEFAULT 0 column — add it via ALTER TABLE IF NOT EXISTS).
   b. Groups events into a compact JSON summary string (<= 2000 chars).
   c. Calls Ollama with a carefully structured prompt that asks the model to
      extract a list of durable profile facts as JSON array:
      `[{"key": "...", "value": {...}, "provenance_event_ids": [...]}]`
      Keys must use dot notation like `user.preferences.seating`.
   d. Parses the JSON response (handles ```json fences).
   e. QC gate: a fact is committed ONLY if its `provenance_event_ids` all
      exist in the events batch (verify before TTL expires).
   f. Upserts each valid fact into `profile` table (INSERT OR REPLACE).
   g. Marks processed events as `distilled=1`.
3. `run_nightly()` — calls `run_batch(max_events=500)` and logs summary.
4. Module-level `if __name__ == "__main__"` block that inserts 3 synthetic
   test events and runs `run_batch()`, printing the extracted profile facts.

## Rules
- Use only Python stdlib + `urllib.request` (no httpx, no requests).
- All SQL must use parameterized queries (no f-string SQL).
- Add Turkish docstrings/comments for critical logic.
- Error handling: log and continue on per-fact errors; never crash the batch.
- Return value of `run_batch`: dict with keys `processed`, `facts_committed`, `errors`.

Write ONLY the Python code inside a ```python ... ``` block. No explanation outside.
""").strip()

draft_raw = call_model(DRAFTER, DRAFT_PROMPT, "TASLAK")
save("01_draft_raw.txt", draft_raw)
draft_code = extract_python(draft_raw)
save("01_draft_code.py", draft_code)

# ── ADIM 2: qwen2.5-coder review ───────────────────────────────────────────
REVIEW_PROMPT = textwrap.dedent(f"""
You are a senior Python code reviewer. Review the following module draft for
**Project KASA** (`src/distill/engine.py`).

## Checklist
1. SQL injection risks? (parameterized queries only)
2. JSON parsing robustness? (handles model fences, malformed output)
3. QC provenance gate implemented correctly?
4. ALTER TABLE for `distilled` column safe on re-run?
5. `run_batch` return dict correct?
6. Any import errors or undefined names?
7. Synthetic test in `__main__` realistic?

## Draft Code
```python
{draft_code[:6000]}
```

Output a corrected, complete ```python ... ``` block.
If no changes needed, output the original unchanged inside the block.
After the block write a one-line Turkish summary of changes made (or "Değişiklik yok.").
""").strip()

review_raw = call_model(REVIEWER, REVIEW_PROMPT, "REVIEW")
save("02_review_raw.txt", review_raw)
final_code = extract_python(review_raw)
save("02_final_code.py", final_code)

# ── ADIM 3: Dosyaya uygula ─────────────────────────────────────────────────
import os
os.makedirs("d:/kasa/src/distill", exist_ok=True)
with open("d:/kasa/src/distill/engine.py", "w", encoding="utf-8") as f:
    f.write(final_code)
print("\n[ORCH] d:/kasa/src/distill/engine.py yazildi.")

# __init__.py
init_path = "d:/kasa/src/distill/__init__.py"
if not os.path.exists(init_path):
    with open(init_path, "w") as f:
        f.write("# distill package\n")

# ── ADIM 4: Syntax check ───────────────────────────────────────────────────
import py_compile, traceback
try:
    py_compile.compile("d:/kasa/src/distill/engine.py", doraise=True)
    print("[ORCH] py_compile: GECTI")
except py_compile.PyCompileError as e:
    print(f"[ORCH] py_compile HATA: {e}")
    sys.exit(1)

print("\n[ORCH] Pipeline tamamlandi.")
