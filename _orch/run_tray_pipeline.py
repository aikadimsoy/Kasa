"""
Tray uygulaması icin lokal model pipeline'i.
deepseek-coder-v2:16b taslak -> qwen2.5-coder:14b review -> uygula
"""
import json, re, os, sys, time
import urllib.request

OLLAMA = "http://localhost:11434/api/generate"
DRAFTER = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
ORCH_DIR = "d:/kasa/_orch"

def call_model(model, prompt, label):
    print(f"\n[ORCH] {label} ({model}) cagiriliyor...", flush=True)
    payload = json.dumps({"model": model, "prompt": prompt, "stream": True,
                          "options": {"temperature": 0.2, "num_predict": 4096}}).encode()
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

# ── ADIM 1: deepseek taslak ─────────────────────────────────────────────────
DRAFT = """
Write the complete Python module `src/tray/app.py` for **Project KASA**.

## Context
- Project KASA is a local-first, encrypted memory vault for agentic browsing on Windows.
- Stack: Python 3.14, PyQt5, Windows.
- The vault database is at `d:/kasa/kasa.db`.
- The MCP server runs at `http://127.0.0.1:8000`.

## What the module must do
1. `KasaTrayApp` class that:
   a. Creates a `QSystemTrayIcon` with a simple colored icon (use `QPixmap` to draw a
      16x16 padlock icon in #4C8DFF on dark background — no external image files).
   b. Shows a context menu with these actions:
      - "Kasa Durumu" (disabled label, shows "Kilitli" or "Acik")
      - Separator
      - "Kasayi Ac" — calls `vault_unlock()`, updates status
      - "Kasayi Kilitle" — calls `vault_lock()`, updates status
      - Separator
      - "Distillasyon Calistir" — calls `run_distill()` in a QThread
      - "Cikis" — quits the application
   c. `vault_unlock()`: sets internal `_locked = False`, shows tray notification
      "Kasa açıldı".
   d. `vault_lock()`: sets internal `_locked = True`, shows tray notification
      "Kasa kilitlendi".
   e. `run_distill()`: runs `DistillEngine.run_batch()` in a `QThread`; on finish,
      shows a tray notification with processed/facts_committed counts.
2. `if __name__ == "__main__"` block that creates `QApplication` and `KasaTrayApp`,
   shows the tray icon, and starts the event loop.

## Rules
- Use only PyQt5 (NOT PyQt6, NOT qfluentwidgets).
- No external image files — draw the icon programmatically with QPainter.
- Import `DistillEngine` from `src.distill.engine` (relative: add d:/kasa to sys.path).
- Turkish comments for critical logic blocks.
- Error handling: catch all exceptions in `run_distill` and show error notification.

Write ONLY the Python code inside a ```python ... ``` block.
""".strip()

draft_raw = call_model(DRAFTER, DRAFT, "TRAY TASLAK")
save("03_tray_draft_raw.txt", draft_raw)
draft_code = extract_python(draft_raw)
save("03_tray_draft_code.py", draft_code)

# ── ADIM 2: qwen review ──────────────────────────────────────────────────────
REVIEW = f"""
Review this PyQt5 system tray module for **Project KASA** (`src/tray/app.py`).

## Checklist
1. Does `QSystemTrayIcon` work without a QWidget parent? (needs QApplication first)
2. Is the icon drawn with QPainter correctly (QPixmap + QPainter + begin/end)?
3. Does QThread usage follow the worker-object pattern (no subclassing QThread directly)?
4. Are tray notifications using `showMessage` correctly?
5. Any import errors or undefined names?
6. Does the `__main__` block call `app.exec_()` (PyQt5 style, not `exec()`)?

## Draft
```python
{draft_code[:6000]}
```

Output corrected complete ```python ... ``` block.
After block: one-line Turkish summary of changes.
""".strip()

review_raw = call_model(REVIEWER, REVIEW, "TRAY REVIEW")
save("04_tray_review_raw.txt", review_raw)
final_code = extract_python(review_raw)
save("04_tray_final_code.py", final_code)

# ── ADIM 3: dosyaya yaz ──────────────────────────────────────────────────────
os.makedirs("d:/kasa/src/tray", exist_ok=True)
open("d:/kasa/src/tray/app.py","w",encoding="utf-8").write(final_code)
print("\n[ORCH] d:/kasa/src/tray/app.py yazildi.")

init_path = "d:/kasa/src/tray/__init__.py"
if not os.path.exists(init_path):
    open(init_path,"w").write("# tray package\n")

# ── ADIM 4: syntax check ─────────────────────────────────────────────────────
import py_compile
try:
    py_compile.compile("d:/kasa/src/tray/app.py", doraise=True)
    print("[ORCH] py_compile: GECTI")
except py_compile.PyCompileError as e:
    print(f"[ORCH] py_compile HATA: {e}")
    sys.exit(1)

print("\n[ORCH] Tray pipeline tamamlandi.")
