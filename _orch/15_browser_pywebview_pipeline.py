"""
Pipeline 15 — KASA Browser (pywebview)
deepseek taslak → qwen review → d:/kasa/src/browser/browser_window.py

pywebview: Windows'ta Edge WebView2 kullanır, kurulum gerekmez.
"""
import json, pathlib, urllib.request, sys

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
KASA     = pathlib.Path("d:/kasa")
OUT_DIR  = KASA / "src" / "browser"

def call_model(model, prompt, label, max_tokens=6000):
    print(f"\n[ORCH] {label} ({model})...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
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
            if not line: continue
            try:
                obj = json.loads(line)
                tok = obj.get("response", "")
                buf.append(tok); print(tok, end="", flush=True)
                if obj.get("done"): break
            except: continue
    print(); return "".join(buf)

def extract_python(text):
    if "```python" in text:
        s = text.find("```python") + 9
        return text[s:text.find("```", s)].strip()
    if "```" in text:
        s = text.find("```") + 3
        return text[s:text.find("```", s)].strip()
    return text.strip()

def syntax_ok(path):
    import subprocess
    r = subprocess.run(
        [sys.executable, "-c",
         f"import ast; ast.parse(open(r'{path}').read()); print('OK')"],
        capture_output=True, text=True
    )
    return "OK" in r.stdout, r.stderr

# ── TASLAK PROMPT ─────────────────────────────────────────────────────────────
DRAFT = """
You are an expert Python developer. Write a complete `browser_window.py` using the
`pywebview` library (already installed). This is for Project KASA local memory vault.

## pywebview basics
- `webview.create_window(title, url, js_api=api_obj, width=1200, height=800)` creates a window
- `webview.start(func=None, args=None)` starts the GUI event loop (BLOCKS)
- JS↔Python bridge: pass a class instance as `js_api`; JS calls `window.pywebview.api.method()`
- Python→JS: `window.evaluate_js(code)` or `window.load_js_string(code)`

## Requirements

### KasaApi class (js_api bridge)
Methods called from JavaScript:
- `ingest(url, title, body_text)` — POST to KASA MCP, non-blocking (use threading.Thread)
  - Endpoint: POST http://localhost:8000/v1/ingest
  - Headers: Authorization: Bearer {token}, Content-Type: application/json
  - Body: {"tool": "event_ingest", "agent_id": "browser", "params": {"source": "browser", "url": url, "title": title, "content": body_text}}
  - Token: read from env KASA_BEARER_TOKEN, fallback to empty string
  - Use urllib.request only (no requests library)
  - On success: print [KASA] ingested: {title}
  - On error: print [KASA] ingest error: {e}  — NEVER raise, never crash

### Content extraction (inject into every page after load)
Use `window.events.loaded += on_loaded` callback.
In on_loaded, evaluate this JS to extract content and call back to Python:
```
(function(){
  var url = window.location.href;
  var title = document.title;
  var body = (document.body ? document.body.innerText : '').substring(0, 3000);
  window.pywebview.api.ingest(url, title, body);
})()
```

### Toolbar (inject as floating HTML overlay)
After creating the window, call window.load_html or evaluate_js to inject a minimal toolbar:
- Back button: `history.go(-1)`
- Forward button: `history.go(1)`
- Reload button: `location.reload()`
- URL input: on Enter → `window.location.href = input.value`
Actually, inject it as a fixed <div> at top of page via evaluate_js after each page load.

### open_browser(url=None) — module-level function
- url defaults to "https://lite.duckduckgo.com/lite"
- Creates KasaApi instance
- Creates webview window
- Calls webview.start() — this blocks until window is closed

## Imports
Only: webview, urllib.request, json, threading, os, sys

## Output
ONLY the complete Python code. No markdown, no explanations.
Start with imports directly.
""".strip()

# ── REVIEW PROMPT ─────────────────────────────────────────────────────────────
REVIEW_TPL = """
Review this pywebview browser_window.py and fix issues.

```python
{draft}
```

Checks:
1. KasaApi.ingest() must run in a Thread (non-blocking) — fix if it blocks the GUI
2. ingest() must NEVER raise an exception — wrap in try/except
3. Bearer token read from os.environ.get("KASA_BEARER_TOKEN", "") — fix if hardcoded
4. webview.start() must be in open_browser(), NOT at module level — fix if wrong
5. Content extraction JS must call window.pywebview.api.ingest(...) — fix if missing
6. open_browser(url=None) must exist at module level — fix if missing
7. No 'requests' library — urllib.request only

Return ONLY corrected Python code. No markdown.
""".strip()

# ── PIPELINE ──────────────────────────────────────────────────────────────────
print("[ORCH] Pipeline 15 — KASA Browser (pywebview)")

raw1 = call_model(DRAFTER, DRAFT, "TASLAK — browser_window.py")
draft_code = extract_python(raw1)

# Draft'i sakla
(KASA / "_orch" / "15_draft_browser_window.py").write_text(draft_code, encoding="utf-8")

raw2 = call_model(REVIEWER, REVIEW_TPL.format(draft=draft_code[:5000]), "REVIEW — browser_window.py")
final_code = extract_python(raw2)

OUT_DIR.mkdir(parents=True, exist_ok=True)

init_path = OUT_DIR / "__init__.py"
if not init_path.exists():
    init_path.write_text(
        'from .browser_window import open_browser\n\n__all__ = ["open_browser"]\n',
        encoding="utf-8"
    )

out_path = OUT_DIR / "browser_window.py"
out_path.write_text(final_code, encoding="utf-8")

ok, err = syntax_ok(out_path)
print(f"\n[ORCH] browser_window.py -> {'SYNTAX OK' if ok else 'HATA: ' + err}")

if ok:
    print(f"\n[ORCH] Pipeline 15 tamamlandi.")
    print(f"  Cikti: {out_path}")
    print(f"\nCalistirmak icin:")
    print(f'  $env:KASA_BEARER_TOKEN = (Get-Content d:/kasa/kasa.toml | Select-String "bearer_token").ToString().Split(\'"\')[1]')
    print(f'  & "C:/Users/REDACTED-USER/AppData/Local/Python/bin/python.exe" -c "from src.browser.browser_window import open_browser; open_browser()"')
else:
    print("[ORCH] Syntax hatasi - elle duzeltme gerekiyor")
    sys.exit(1)
