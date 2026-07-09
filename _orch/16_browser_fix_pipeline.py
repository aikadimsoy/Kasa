"""
Pipeline 16 — Browser Veri Akisi Duzeltmesi
deepseek taslak -> qwen review -> dosyalara yaz

Sorunlar:
  1. browser_window.py payload uyusmazligi (url/title/content:str vs source/type/content:dict)
  2. browser agent icin events:write izni yok
  3. Toolbar'da reflex gostergesi yok
  4. Cerez yakalama eksik
  5. MCP sunucu baslama komutu eksik

Hedef dosyalar:
  d:/kasa/src/browser/browser_window.py  (payload fix + cookie + reflex)
  d:/kasa/src/mcp_server/server.py       (browser agent auto-grant events:write)
"""
import json, pathlib, sys, urllib.request

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
KASA     = pathlib.Path("d:/kasa")

def call_model(model, prompt, label, max_tokens=6000):
    print(f"\n[ORCH] {label} ({model})...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": 0.2, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(
        OLLAMA, data=payload, headers={"Content-Type": "application/json"}
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

# ════════════════════════════════════════════════════════════════
# GOREV 1 — browser_window.py duzeltme
# ════════════════════════════════════════════════════════════════

browser_current = (KASA / "src" / "browser" / "browser_window.py").read_text(encoding="utf-8")

BROWSER_DRAFT = f"""
You are an expert Python + pywebview developer. Fix this browser_window.py module.

## Current code:
```python
{browser_current}
```

## Problems to fix:

### Fix 1 — Payload mismatch
Current _post() sends:
  {{"tool": "event_ingest", "agent_id": "browser", "params": {{"source": "browser", "url": url, "title": title, "content": body_text}}}}

VaultTools.event_ingest() signature is:
  def event_ingest(self, source: str, type: str, content: dict, ttl_days: int = 30)

Fix: change params to:
  {{"source": "browser", "type": "page_visit", "content": {{"url": url, "title": title, "text": body_text, "cookies": cookies}}, "ttl_days": 30}}

### Fix 2 — Cookie capture
In _INGEST_JS, extract cookies via document.cookie (only non-HttpOnly cookies are accessible).
Parse "name=value; name2=value2" into a list of {{"name": ..., "value": ...}} dicts (max 20 cookies).
Add cookies as 4th argument to window.pywebview.api.ingest(url, title, body, cookies_json).

Update KasaApi.ingest() signature to: ingest(self, url, title, body_text, cookies_json="[]")
In _post(), parse cookies_json string as JSON list.

### Fix 3 — Toolbar reflex indicator
Add a KasaApi.show_status(message, color) method that stores a reference to the pywebview window
and calls win.evaluate_js to update a status element in the toolbar.

Add a status span in _TOOLBAR_JS with id="_kasa_status" (right side of toolbar).
After successful ingest: call show_status("ingested", "#a6e3a1") (green)
After ingest error: call show_status("!", "#f38ba8") (red, no details)

To give KasaApi access to the window, add set_window(win) method:
  def set_window(self, win): self._win = win

Call api.set_window(win) in open_browser() after creating the window.
In show_status(), use self._win if set, else silently skip.

## Rules:
- Keep ALL other code intact
- No new dependencies
- Return ONLY the complete fixed Python code. No markdown.
""".strip()

raw1 = call_model(DRAFTER, BROWSER_DRAFT, "TASLAK — browser_window.py duzeltme")
draft1 = extract_python(raw1)
(KASA / "_orch" / "16_draft_browser_window.py").write_text(draft1, encoding="utf-8")

REVIEW_BROWSER = f"""
Review this fixed browser_window.py. Check:

```python
{draft1[:5000]}
```

1. _post() params must be: source="browser", type="page_visit", content=dict with url/title/text/cookies, ttl_days=30
2. ingest() must accept 4 args: url, title, body_text, cookies_json="[]"
3. cookies extracted as list of name/value dicts, max 20
4. KasaApi must have set_window(win) and show_status(msg, color) methods
5. _TOOLBAR_JS must include a span id="_kasa_status" on the right side
6. show_status() must update _kasa_status via evaluate_js, wrapped in try/except (never crash)
7. webview.start() must be called ONCE in open_browser(), not recursively

Return ONLY corrected Python code. No markdown.
""".strip()

raw1r = call_model(REVIEWER, REVIEW_BROWSER, "REVIEW — browser_window.py")
browser_final = extract_python(raw1r)

browser_path = KASA / "src" / "browser" / "browser_window.py"
(KASA / "_orch" / "16_browser_backup.py").write_text(browser_current, encoding="utf-8")
browser_path.write_text(browser_final, encoding="utf-8")
ok1, err1 = syntax_ok(browser_path)
print(f"\n[ORCH] browser_window.py -> {'SYNTAX OK' if ok1 else 'HATA: ' + err1}")

# ════════════════════════════════════════════════════════════════
# GOREV 2 — server.py: browser agent auto-grant events:write
# ════════════════════════════════════════════════════════════════

server_current = (KASA / "src" / "mcp_server" / "server.py").read_text(encoding="utf-8")

SERVER_DRAFT = f"""
You are a FastAPI developer. Add ONE small feature to this server.py.

## Current server.py:
```python
{server_current}
```

## Feature to add: auto-grant events:write to browser agent on startup

In the lifespan() context manager, AFTER the schema setup loop, add:
```python
# browser agent icin events:write otomatik izni (startup)
from ..mcp_server.tools import VaultTools
_browser_tools = VaultTools(VAULT_INSTANCE, agent_id="system")
_browser_tools.grant_permission_for("browser", "events:write")
```

BUT: VaultTools.grant_permission() only grants for self.agent_id.
Instead, insert directly into permissions table:
```python
conn.execute(
    "INSERT OR IGNORE INTO permissions (agent_id, scope, granted_at) VALUES (?, ?, ?)",
    ("browser", "events:write", __import__('time').time())
)
conn.commit()
```

Add this block in lifespan(), after the schema loop and commit, before yield.

## Rules:
- Keep ALL existing code intact
- Only add the auto-grant block in lifespan()
- Return ONLY the complete updated server.py. No markdown.
""".strip()

raw2 = call_model(DRAFTER, SERVER_DRAFT, "TASLAK — server.py auto-grant")
draft2 = extract_python(raw2)

REVIEW_SERVER = f"""
Review this updated server.py:

```python
{draft2[:5000]}
```

1. lifespan() must contain: INSERT OR IGNORE INTO permissions ... ("browser", "events:write", time.time())
2. This insert must happen AFTER the schema setup loop
3. All existing endpoints must be preserved (execute_tool, ingest, health check)
4. Bearer token auth must still be on /v1/execute_tool and /v1/ingest
5. GET / must still be auth-free

Return ONLY corrected server.py. No markdown.
""".strip()

raw2r = call_model(REVIEWER, REVIEW_SERVER, "REVIEW — server.py auto-grant")
server_final = extract_python(raw2r)

server_path = KASA / "src" / "mcp_server" / "server.py"
(KASA / "_orch" / "16_server_backup.py").write_text(server_current, encoding="utf-8")
server_path.write_text(server_final, encoding="utf-8")
ok2, err2 = syntax_ok(server_path)
print(f"\n[ORCH] server.py -> {'SYNTAX OK' if ok2 else 'HATA: ' + err2}")

# ════════════════════════════════════════════════════════════════
print("\n[ORCH] Pipeline 16 tamamlandi.")
if ok1 and ok2:
    print("  Her iki dosya da SYNTAX OK")
    print("\nTest adımlari:")
    print("  1. MCP sunucu: cd d:/kasa && python -m src.mcp_server.server")
    print("  2. Browser: python -c \"from src.browser.browser_window import open_browser; open_browser()\"")
    print("  3. Bir siteye gir -> toolbar'da yesil 'ingested' gormeli")
    print("  4. DB kontrol: python -c \"import sqlite3,json; ...")
else:
    if not ok1: print(f"  browser_window.py HATA: {err1}")
    if not ok2: print(f"  server.py HATA: {err2}")
    sys.exit(1)
