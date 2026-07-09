"""
run.py pipeline — MCP sunucu + tray uygulamasini birlikte baslatan
ana giris noktasini uretir.
"""
import json, re, os, sys
import urllib.request

OLLAMA = "http://localhost:11434/api/generate"
DRAFTER = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
ORCH_DIR = "d:/kasa/_orch"

def call_model(model, prompt, label):
    print(f"\n[ORCH] {label} ({model})...", flush=True)
    payload = json.dumps({"model": model, "prompt": prompt, "stream": True,
                          "options": {"temperature": 0.2, "num_predict": 3000}}).encode()
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type":"application/json"})
    result = []
    with urllib.request.urlopen(req, timeout=300) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line: continue
            try:
                obj = json.loads(line)
                tok = obj.get("response","")
                result.append(tok); print(tok, end="", flush=True)
                if obj.get("done"): break
            except: continue
    print(); return "".join(result)

def save(name, content):
    os.makedirs(ORCH_DIR, exist_ok=True)
    path = f"{ORCH_DIR}/{name}"
    open(path,"w",encoding="utf-8").write(content)
    print(f"[ORCH] Kaydedildi: {path}")

def extract_python(text):
    m = re.search(r"```python\s*\r?\n(.*?)```", text, re.DOTALL)
    return m.group(1) if m else text

DRAFT = """
Write `run.py` — the main entry point for **Project KASA** at `d:/kasa/run.py`.

## What it must do
1. Parse CLI args: `--vault-path` (default `d:/kasa`), `--mcp-port` (default 8000),
   `--no-tray` (headless mode), `--distill-now` (run distillation immediately and exit).
2. Initialize the vault (`Vault` from `src.vault.database`) and ensure schema exists.
3. Start the MCP server (`uvicorn src.mcp_server.server:app`) in a **daemon thread**
   using `uvicorn.run()` with `host="127.0.0.1"`.
4. Start the distillation scheduler (`DistillScheduler` from `src.distill.scheduler`)
   as a daemon thread.
5. If `--distill-now`: call `scheduler.run_now()`, print result as JSON, exit 0.
6. If `--no-tray`: block the main thread with `threading.Event().wait()`.
7. Otherwise: start the PyQt5 `QApplication` and `KasaTrayApp` from `src.tray.app`,
   call `app.setQuitOnLastWindowClosed(False)`, run the Qt event loop.
8. On clean exit: log shutdown message.

## Rules
- `sys.path.insert(0, str(Path(__file__).parent))` at top so imports work.
- Use `argparse` for CLI.
- Use `threading.Thread(daemon=True)` for uvicorn — never block main thread.
- Give uvicorn a 1-second startup grace period (`time.sleep(1)`) before tray.
- Turkish comments for key logic blocks.
- All imports inside functions to avoid circular import issues when uvicorn
  reloads (wrap heavy imports after argparse).
- Write ONLY the Python code in a ```python ... ``` block.
""".strip()

draft_raw = call_model(DRAFTER, DRAFT, "RUN.PY TASLAK")
save("05_run_draft_raw.txt", draft_raw)
draft_code = extract_python(draft_raw)
save("05_run_draft_code.py", draft_code)

REVIEW = f"""
Review this `run.py` entry point for Project KASA.

## Checklist
1. Does the uvicorn thread start correctly without blocking main thread?
2. Is argparse used correctly (--vault-path, --mcp-port, --no-tray, --distill-now)?
3. Does the tray app get `setQuitOnLastWindowClosed(False)` called?
4. Is sys.path set correctly so `src.*` imports work?
5. Are there any circular import risks?
6. Does `--distill-now` path exit cleanly?
7. Any undefined names or missing imports?

## Draft
```python
{draft_code[:5000]}
```

Output corrected complete ```python ... ``` block.
After block: one-line Turkish summary of changes.
""".strip()

review_raw = call_model(REVIEWER, REVIEW, "RUN.PY REVIEW")
save("06_run_review_raw.txt", review_raw)
final_code = extract_python(review_raw)
save("06_run_final_code.py", final_code)

open("d:/kasa/run.py","w",encoding="utf-8").write(final_code)
print("\n[ORCH] d:/kasa/run.py yazildi.")

import py_compile
try:
    py_compile.compile("d:/kasa/run.py", doraise=True)
    print("[ORCH] py_compile: GECTI")
except py_compile.PyCompileError as e:
    print(f"[ORCH] HATA: {e}"); sys.exit(1)

print("[ORCH] run.py pipeline tamamlandi.")
