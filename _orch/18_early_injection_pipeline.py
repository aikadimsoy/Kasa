"""
KASA Orkestrasyon — Layer #1: Erken Enjeksiyon (pre-load spoof) v1.0
deepseek taslak -> qwen review. Cikti: browser_window.py'ye _register_early_privacy()
helper'i + on_loaded() icinde tek-seferlik cagri.

Hedef: _PRIVACY_JS'i WebView2'nin AddScriptToExecuteOnDocumentCreatedAsync API'si ile
sayfa scriptlerinden ONCE calistirmak. Boylece PerimeterX/Akamai gercek degerleri
okuyamadan spoof devrede olur.
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
        "options": {"temperature": 0.1, "num_predict": max_tokens}
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

def extract_py(text):
    m = re.search(r"```(?:python)?\n([\s\S]+?)```", text)
    return m.group(1).strip() if m else text.strip()

DRAFT_PROMPT = r'''Write a single Python function for a pywebview 6.2.1 app (Windows, EdgeChromium/WebView2 backend).

Context (already verified — use EXACTLY these API paths):
- pywebview window object `win` has attribute `win.uid`
- `from webview.platforms.winforms import BrowserView`
- `BrowserView.instances` is a dict keyed by `win.uid`; value is a WinForms.Form (BrowserForm)
- that form has `.browser` (EdgeChrome), and `.browser.webview.CoreWebView2` is the CoreWebView2 object (may be None until initialized)
- WebView2 API calls MUST run on the UI thread -> marshal via the form's `.BeginInvoke(Action(...))`
- `from System import Action`
- The CoreWebView2 method to register a script that runs BEFORE any page script on every future navigation is:
      core.AddScriptToExecuteOnDocumentCreatedAsync(js_string)
- The JS to register is a module-level global string constant named `_PRIVACY_JS` (already defined elsewhere in the module).

Write ONLY this function:

def _register_early_privacy(win):
    """CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync ile _PRIVACY_JS'i
    sayfa scriptlerinden ONCE calistir. Tum sonraki navigasyonlarda gecerli.
    Basari/hata durumunu bool doner."""

Requirements:
- import BrowserView and Action inside the function (lazy).
- get instance via BrowserView.instances.get(win.uid); if None return False.
- define an inner function that reads core = instance.browser.webview.CoreWebView2, if core is None return, else core.AddScriptToExecuteOnDocumentCreatedAsync(_PRIVACY_JS).
- call instance.BeginInvoke(Action(inner)).
- wrap everything in try/except; on exception print("[KASA] erken enjeksiyon: {e}") and return False.
- return True after scheduling BeginInvoke.
- No other code, no example usage. Output only the function in a python code block.
'''

def run():
    draft = extract_py(call_model(DRAFTER, DRAFT_PROMPT, "DRAFT — early injection helper"))
    review_prompt = (
        "Review this Python function for a pywebview WebView2 app. Verify: (1) lazy imports of "
        "BrowserView and Action inside function, (2) BrowserView.instances.get(win.uid) with None "
        "check returning False, (3) inner function reads instance.browser.webview.CoreWebView2, None "
        "check, else calls core.AddScriptToExecuteOnDocumentCreatedAsync(_PRIVACY_JS), (4) "
        "instance.BeginInvoke(Action(inner)) to marshal to UI thread, (5) try/except printing "
        "'[KASA] erken enjeksiyon:' and returning False, (6) returns True after scheduling. Fix any "
        "issue. Output ONLY the corrected function in a python code block.\n\n```python\n"
        + draft + "\n```"
    )
    final = extract_py(call_model(REVIEWER, review_prompt, "REVIEW — early injection helper"))
    out_path = "d:/kasa/_orch/18_early_injection_helper.py"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(final + "\n")
    print(f"\n[ORCH] Helper yazildi -> {out_path}")
    print("[ORCH] Claude bunu dogrulayip browser_window.py'ye splice edecek.")

if __name__ == "__main__":
    run()
