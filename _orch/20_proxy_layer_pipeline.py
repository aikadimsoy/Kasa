"""
KASA Orkestrasyon — Layer #2: Proxy / IP Gizleme (iskelet) v1.0
deepseek taslak -> qwen review. IKI artifact uretir (auto-splice YOK; Claude splice eder):
  - 20_proxy_python.py  : KasaApi.get_proxy/set_proxy + _apply_proxy_env() + startup snippet
  - 20_proxy_sidebar.js : renderAg() bolumu + rail butonu wiring snippet

Teknik gercek (deepseek'e AYNEN veriliyor):
  WebView2 proxy, environment olusmadan ONCE os.environ ile verilir:
    os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = '--proxy-server=<addr>'
  Calisirken sicak degistirilemez -> degisiklik yeniden baslatmayla gecer.
  Config dosyasi: d:/kasa/browser_config.json  { "proxy_enabled": bool, "proxy_address": str }
"""
import json, sys, re
import urllib.request

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"

def call_model(model, prompt, label, max_tokens=4096):
    print(f"\n[ORCH] {label} ({model}) cagiriliyor...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": 0.12, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    out = []
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                out.append(obj.get("response", ""))
                print(obj.get("response", ""), end="", flush=True)
                if obj.get("done"):
                    break
            except json.JSONDecodeError:
                continue
    print()
    return "".join(out)

def extract(text, lang):
    m = re.search(r"```(?:" + lang + r")?\n([\s\S]+?)```", text)
    return m.group(1).strip() if m else text.strip()

# ── PYTHON artifact ───────────────────────────────────────────────────────────
PY_DRAFT = r'''Write Python code for a pywebview 6.2.1 app (Windows, WebView2 backend).

VERIFIED FACTS — use EXACTLY:
- WebView2 reads proxy from the process environment variable
  WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS. It MUST be set BEFORE the WebView2
  environment is created (i.e. before webview.create_window / webview.start).
- Proxy is applied by setting that env var to "--proxy-server=<address>".
- Config is a JSON file at "d:/kasa/browser_config.json" with keys:
    "proxy_enabled" (bool), "proxy_address" (str, e.g. "socks5://127.0.0.1:9150").
- `import os, json` already available at top of module.

Write EXACTLY these three things, nothing else:

1) A module-level constant:
   _BROWSER_CONFIG_PATH = "d:/kasa/browser_config.json"

2) A module-level function `_read_browser_config()` that returns a dict.
   - open _BROWSER_CONFIG_PATH, json.load it, return it.
   - on ANY exception return {"proxy_enabled": False, "proxy_address": ""}.

3) A module-level function `_apply_proxy_env()`:
   - cfg = _read_browser_config()
   - addr = (cfg.get("proxy_address") or "").strip()
   - if cfg.get("proxy_enabled") and addr:
       os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--proxy-server=" + addr
       print("[KASA] proxy aktif: " + addr)
     else:
       print("[KASA] proxy kapali.")

4) TWO methods to be added INTO the existing `class KasaApi` (output them as
   standalone methods with 4-space indent, I will paste them into the class):
   - def get_proxy(self): return _read_browser_config()
   - def set_proxy(self, enabled, address):
       write {"proxy_enabled": bool(enabled), "proxy_address": str(address or "")}
       to _BROWSER_CONFIG_PATH via json.dump; wrap in try/except printing
       "[KASA] set_proxy hata: {e}"; return the dict on success, else return
       {"proxy_enabled": False, "proxy_address": ""}.

Output ONLY one python code block. No usage examples, no comments beyond docstrings.'''

PY_REVIEW = ('Review this Python for a pywebview WebView2 app. Verify: (1) '
    '_BROWSER_CONFIG_PATH constant, (2) _read_browser_config() returns dict, '
    'safe default on exception, (3) _apply_proxy_env() sets '
    'os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"]="--proxy-server="+addr '
    'ONLY when enabled and addr non-empty, else prints "proxy kapali", (4) '
    'get_proxy/set_proxy methods with 4-space indent, set_proxy json.dumps to file '
    'with try/except. Fix bugs. Output ONLY the corrected python code block.\n\n'
    '```python\n{DRAFT}\n```')

# ── JS artifact ───────────────────────────────────────────────────────────────
JS_DRAFT = r'''You are writing a JavaScript SNIPPET to extend an existing collapsible sidebar
in the KASA browser (injected via pywebview evaluate_js). CSS design tokens exist on
:root (--kasa-n950/n900/n800/n700/n500/n300/n100, --kasa-primary, --kasa-secure).
There are existing CSS classes: .kasa-row (flex space-between), panel inputs styled via
"#_kasa_panel input[type=text]" and "#_kasa_panel select". A `panel` DOM element and a
`RENDER` object map already exist. `window.pywebview.api.get_proxy()` returns a Promise
resolving to {proxy_enabled:bool, proxy_address:string}. `window.pywebview.api.set_proxy(enabled,address)`
persists it.

Write ONE JavaScript function `renderAg()` (nothing else) that:
1. Sets panel.innerHTML = '<h2>Ag / Proxy</h2>';
2. Builds a toggle row (label "Proxy kullan" + a checkbox #_kasa_proxy_on) using a div.className='kasa-row'.
3. Builds a text input #_kasa_proxy_addr (type=text) with placeholder "socks5://127.0.0.1:9150",
   inside a <label>Proxy adresi</label>.
4. Builds a small button "Tor (127.0.0.1:9150)" that when clicked sets the address input value to
   "socks5://127.0.0.1:9150".
5. Adds a note div (font-size 11px, color var(--kasa-n500)):
   "Degisiklik tarayici yeniden baslatilinca gecerli olur. Bos + kapali = dogrudan baglanti (gercek IP)."
6. Adds a "Kaydet" button (background var(--kasa-primary), color #fff) that calls
   window.pywebview.api.set_proxy(checkbox.checked, input.value).
7. On entry, calls window.pywebview.api.get_proxy().then(function(cfg){ ... }) to populate
   checkbox.checked = cfg.proxy_enabled and input.value = cfg.proxy_address || ''.
8. Wrap DOM ops so a missing pywebview api does not throw (typeof check).
Use document.createElement + addEventListener (NO inline onclick, page CSP blocks it).
Output ONLY one javascript code block containing exactly `function renderAg() { ... }`.'''

JS_REVIEW = ('Review this JS function renderAg() for the KASA sidebar. Verify: (1) sets '
    'panel.innerHTML heading, (2) checkbox #_kasa_proxy_on in a .kasa-row, (3) text input '
    '#_kasa_proxy_addr with placeholder, (4) Tor preset button fills address, (5) note div, '
    '(6) Kaydet button calls window.pywebview.api.set_proxy(checked,value), (7) populates from '
    'window.pywebview.api.get_proxy().then(...), guarded by typeof check, (8) uses addEventListener '
    'not inline onclick, (9) valid JS, balanced braces. Fix bugs. Output ONLY the corrected '
    'javascript code block.\n\n```javascript\n{DRAFT}\n```')

def run():
    # Python artifact
    py_draft = extract(call_model(DRAFTER, PY_DRAFT, "DRAFT — proxy python"), "python")
    py_final = extract(call_model(REVIEWER, PY_REVIEW.replace("{DRAFT}", py_draft),
                                  "REVIEW — proxy python"), "python")
    with open("d:/kasa/_orch/20_proxy_python.py", "w", encoding="utf-8") as f:
        f.write(py_final + "\n")
    print("\n[ORCH] yazildi -> 20_proxy_python.py")

    # JS artifact
    js_draft = extract(call_model(DRAFTER, JS_DRAFT, "DRAFT — proxy sidebar js"), "javascript")
    js_final = extract(call_model(REVIEWER, JS_REVIEW.replace("{DRAFT}", js_draft),
                                  "REVIEW — proxy sidebar js"), "javascript")
    with open("d:/kasa/_orch/20_proxy_sidebar.js", "w", encoding="utf-8") as f:
        f.write(js_final + "\n")
    print("[ORCH] yazildi -> 20_proxy_sidebar.js")
    print("\n[ORCH] TAMAM. Claude dogrulayip browser_window.py'ye splice edecek "
          "(startup _apply_proxy_env cagrisi + KasaApi metodlari + renderAg + rail butonu).")

if __name__ == "__main__":
    run()
