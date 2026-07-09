"""
KASA Orkestrasyon — Fix: yeni-pencere ayni pencerede + DevTools/inceleme acik v1.0
deepseek taslak -> qwen review. Cikti: 24_newwindow_devtools_fix.py
  -> Claude dogrulayip browser_window.py open_browser()'a splice eder.

KESIF (pywebview 6.2.1 kaynagi, edgechromium.py):
  - on_new_window_request(self, sender, args):
        args.set_Handled(True)
        if webview_settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']:
            webbrowser.open(str(args.get_Uri()))   # <-- sistem Chrome'unu acan bu
        else:
            self.load_url(str(args.get_Uri()))      # <-- ayni pencerede acar
  - on_webview_ready: settings.AreDevToolsEnabled / AreDefaultContextMenusEnabled /
        AreBrowserAcceleratorKeysEnabled  hepsi = _state['debug'] ile ayarlanir.
        _state['debug'] -> webview.start(debug=...) parametresinden gelir.

SONUC: cozum pywebview'in KENDI public API'si ile 2 satir:
  1) webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False   (create_window'dan ONCE)
  2) webview.start(debug=True)   (mevcut webview.start() yerine)
Custom NewWindowRequested handler'a GEREK YOK (cift-navigasyona yol acar) -> kaldirilmali.
"""
import json, sys, re
import urllib.request

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"

def call_model(model, prompt, label, max_tokens=1200):
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

DRAFT = r'''You are fixing a Python pywebview 6.2.1 desktop browser app (KASA).

TWO BUGS:
1) Clicking an ad / target=_blank link opens the URL in the EXTERNAL system browser
   (Chrome) instead of inside the app window.
2) Right-click "Inspect" and F12 DevTools do not work.

VERIFIED FACTS from pywebview source (webview/platforms/edgechromium.py):
- pywebview ALREADY registers its own NewWindowRequested handler:
    def on_new_window_request(self, sender, args):
        args.set_Handled(True)
        if webview_settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']:
            webbrowser.open(str(args.get_Uri()))     # opens external Chrome
        else:
            self.load_url(str(args.get_Uri()))       # opens in SAME window
- DevTools/context-menu/accelerator keys are enabled only when debug is on:
    settings.AreDevToolsEnabled            = _state['debug']
    settings.AreDefaultContextMenusEnabled = _state['debug']
    settings.AreBrowserAcceleratorKeysEnabled = _state['debug']
  and _state['debug'] comes from webview.start(debug=...).

Therefore the CORRECT minimal fix uses ONLY pywebview's public API, no custom
CoreWebView2 event handler:
  A) Before webview.create_window(...), set:
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False
  B) Change  webview.start()  to  webview.start(debug=True)

Current relevant code in open_browser():
    def open_browser(url="https://lite.duckduckgo.com/lite"):
        _apply_proxy_env()
        api = KasaApi()
        win = webview.create_window("KASA Browser", url, js_api=api, width=1280, height=860)
        ...
        webview.start()

TASK: Output ONLY one python code block containing exactly these two statements,
each with a short Turkish comment, in the order they should appear:
1) the webview.settings line (goes right after _apply_proxy_env()).
2) the webview.start(debug=True) line (replaces webview.start()).
Do NOT write a custom NewWindowRequested handler. Do NOT add anything else.'''

REVIEW = ('Review this Python fix for a pywebview 6.2.1 app. It must contain EXACTLY:\n'
    "  webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False\n"
    "  webview.start(debug=True)\n"
    'Verify: (1) the settings key name is EXACTLY OPEN_EXTERNAL_LINKS_IN_BROWSER and value is '
    'False (Python bool, capital F); (2) debug=True is passed to webview.start; (3) there is NO '
    'custom CoreWebView2 NewWindowRequested handler (pywebview already handles it). '
    'Fix any deviation. Output ONLY the corrected python code block with Turkish comments.\n\n'
    '```python\n{DRAFT}\n```')

def run():
    draft = extract_py(call_model(DRAFTER, DRAFT, "DRAFT — newwindow/devtools fix"))
    final = extract_py(call_model(REVIEWER, REVIEW.replace("{DRAFT}", draft), "REVIEW — newwindow/devtools fix"))
    with open("d:/kasa/_orch/24_newwindow_devtools_fix.py", "w", encoding="utf-8") as f:
        f.write(final + "\n")
    print("\n[ORCH] yazildi -> 24_newwindow_devtools_fix.py")
    print("[ORCH] Claude dogrulayip open_browser()'a splice edecek (+ custom handler'i geri alacak).")

if __name__ == "__main__":
    run()
