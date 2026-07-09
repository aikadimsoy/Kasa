"""
Pipeline 13 — KASA Browser Modülü
deepseek taslak yazar → qwen gözden geçirir → d:/kasa/src/browser/ dosyalarına yazar
"""
import json, os, pathlib, urllib.request

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
OUT_DIR  = pathlib.Path("d:/kasa/src/browser")
ORCH     = pathlib.Path("d:/kasa/_orch")

def call_model(model, prompt, label, max_tokens=6000):
    print(f"\n[ORCH] {label} ({model})...", flush=True)
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.2, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(
        OLLAMA, data=payload,
        headers={"Content-Type": "application/json"}
    )
    buf = []
    with urllib.request.urlopen(req, timeout=300) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                tok = obj.get("response", "")
                buf.append(tok)
                print(tok, end="", flush=True)
                if obj.get("done"):
                    break
            except Exception:
                continue
    print()
    return "".join(buf)

def extract_python(text):
    """Markdown kod bloğundan Python kodunu çıkar."""
    if "```python" in text:
        start = text.find("```python") + 9
        end = text.find("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        return text[start:end].strip()
    return text.strip()

# ─── TASLAK PROMPT ────────────────────────────────────────────────────────────
DRAFT_PROMPT = """
You are an expert PyQt5 developer. Write a complete, production-ready Python module.

## Task
Create `browser_window.py` — a standalone embedded browser for Project KASA.

## Requirements

### BrowserWindow class (QMainWindow)
- Uses `QWebEngineView` with `QWebEngineProfile(offTheRecord=True)` — zero disk persistence
- Toolbar: back, forward, reload, URL bar (QLineEdit), go button
- Status bar shows load progress (QProgressBar, hidden when 100%)
- Window title: "KASA Browser — {page_title}"
- Keyboard shortcuts: Ctrl+L (focus URL bar), Ctrl+R (reload), Alt+Left/Right (back/forward)
- Default home URL: "about:blank"

### Content extraction
- Connect to `loadFinished` signal
- On page load, run JavaScript to extract: url, title, body text (first 2000 chars of document.body.innerText)
- Call `self._ingest_to_kasa(url, title, body_text)` with extracted data

### KASA MCP ingest
- `_ingest_to_kasa(url, title, body_text)` — POST to `http://localhost:8000/v1/ingest`
- Payload: `{"source": "browser", "url": url, "title": title, "content": body_text}`
- Use `urllib.request` only (no requests library)
- Run in a QThread to avoid blocking UI
- On success: print `[KASA] ingested: {title}`
- On error: print `[KASA] ingest error: {e}` — do NOT crash the browser

### IngestWorker(QThread)
- Takes url, title, body_text
- Posts to MCP in background
- Emits `done = pyqtSignal(str)` with result message

### Module-level `open_browser(url=None)` function
- Creates QApplication if not exists
- Creates and shows BrowserWindow
- Navigates to url if provided

## Imports
Only use: PyQt5.QtWidgets, PyQt5.QtWebEngineWidgets, PyQt5.QtCore, PyQt5.QtGui, urllib.request, json, sys

## Output
Return ONLY the complete Python code. No explanations. No markdown headers.
Start with the imports directly.
""".strip()

# ─── REVIEW PROMPT ────────────────────────────────────────────────────────────
REVIEW_PROMPT_TPL = """
You are a senior PyQt5 code reviewer. Review this `browser_window.py` module and fix any issues.

## Module to review:
```python
{draft}
```

## Check for:
1. `QWebEngineProfile` must use `offTheRecord=True` parameter — fix if wrong
2. `loadFinished` signal must be connected — fix if missing
3. JavaScript extraction must use `page().runJavaScript()` with callback — fix if blocking
4. `IngestWorker(QThread)` must exist and be used — fix if missing
5. `urllib.request` only for HTTP — remove any `requests` import
6. No `app.exec_()` inside `BrowserWindow.__init__` — it belongs in `open_browser()`
7. `open_browser()` function must exist at module level

## Output
Return ONLY the corrected, complete Python code. No explanations. No markdown.
Start with imports directly.
""".strip()

# ─── PIPELINE ÇALIŞTIR ────────────────────────────────────────────────────────
print("[ORCH] Pipeline 13 başlıyor — KASA Browser Modülü")
print(f"[ORCH] Hedef: {OUT_DIR}")

# Adım 1: deepseek taslak yazar
raw_draft = call_model(DRAFTER, DRAFT_PROMPT, "TASLAK — BrowserWindow")
draft_code = extract_python(raw_draft)

draft_path = ORCH / "13_draft_browser_window.py"
draft_path.write_text(draft_code, encoding="utf-8")
print(f"[ORCH] Taslak kaydedildi: {draft_path}")

# Adım 2: qwen gözden geçirir
review_prompt = REVIEW_PROMPT_TPL.format(draft=draft_code[:5000])
raw_review = call_model(REVIEWER, review_prompt, "REVIEW — browser_window.py")
final_code = extract_python(raw_review)

# Adım 3: dosyaya yaz
OUT_DIR.mkdir(parents=True, exist_ok=True)

init_path = OUT_DIR / "__init__.py"
if not init_path.exists():
    init_path.write_text('from .browser_window import BrowserWindow, open_browser\n\n__all__ = ["BrowserWindow", "open_browser"]\n', encoding="utf-8")
    print(f"[ORCH] __init__.py oluşturuldu: {init_path}")

out_path = OUT_DIR / "browser_window.py"
out_path.write_text(final_code, encoding="utf-8")
print(f"\n[ORCH] ✅ browser_window.py yazıldı: {out_path}")

# Adım 4: syntax kontrolü
import subprocess, sys
result = subprocess.run(
    [sys.executable, "-c", f"import ast; ast.parse(open(r'{out_path}').read()); print('SYNTAX OK')"],
    capture_output=True, text=True
)
if "SYNTAX OK" in result.stdout:
    print("[ORCH] ✅ Syntax kontrolü geçti")
else:
    print(f"[ORCH] ⚠️  Syntax hatası:\n{result.stderr}")
    print("[ORCH] Taslak dosya korunuyor, elle inceleme gerekiyor")

print("\n[ORCH] Pipeline 13 tamamlandı.")
print(f"[ORCH] Çıktı: {out_path}")
print(f"[ORCH] Taslak: {draft_path}")
