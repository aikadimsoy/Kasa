import webview
import urllib.request
import json
import threading
import os

_TOOLBAR_JS = """
(function() {
    if (document.getElementById('_kasa_toolbar')) return;
    var bar = document.createElement('div');
    bar.id = '_kasa_toolbar';
    bar.style.cssText = 'position:fixed;top:0;left:0;right:0;height:36px;background:#1e1e2e;' +
        'display:flex;align-items:center;gap:4px;padding:0 8px;z-index:2147483647;' +
        'font-family:sans-serif;font-size:13px;box-shadow:0 2px 6px rgba(0,0,0,0.4);';
    bar.innerHTML = '<button onclick="history.go(-1)" style="color:#cdd6f4;background:#313244;border:none;' +
        'border-radius:4px;padding:4px 10px;cursor:pointer;">&#8592;</button>' +
        '<button onclick="history.go(1)" style="color:#cdd6f4;background:#313244;border:none;' +
        'border-radius:4px;padding:4px 10px;cursor:pointer;">&#8594;</button>' +
        '<button onclick="location.reload()" style="color:#cdd6f4;background:#313244;border:none;' +
        'border-radius:4px;padding:4px 10px;cursor:pointer;">&#8635;</button>' +
        '<input id="_kasa_url" type="text" value="'+window.location.href+'" ' +
        'style="flex:1;background:#313244;color:#cdd6f4;border:1px solid #45475a;' +
        'border-radius:4px;padding:4px 8px;font-size:13px;" ' +
        'onkeydown="if(event.key===\\'Enter\\'){window.location.href=this.value}" />' +
        '<span id="_kasa_status" style="color:#6c7086;font-size:11px;padding:0 6px;">KASA</span>';
    document.body.style.marginTop = '40px';
    document.body.insertBefore(bar, document.body.firstChild);
})();
"""

_INGEST_JS = """
(function() {
    var url = window.location.href;
    var title = document.title;
    var body = (document.body ? document.body.innerText : '').substring(0, 3000);
    var cookies = document.cookie.split(';').map(c => {
        let [name, value] = c.trim().split('=');
        return { name, value };
    }).slice(0, 20);
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.ingest(url, title, body, JSON.stringify(cookies));
    }
})();
"""


class KasaApi:
    def __init__(self):
        self.token = os.environ.get("KASA_BEARER_TOKEN", "")
        self._win = None

    def set_window(self, win):
        self._win = win

    def ingest(self, url, title, body_text, cookies_json="[]"):
        threading.Thread(target=self._post, args=(url, title, body_text, cookies_json), daemon=True).start()

    def _post(self, url, title, body_text, cookies_json):
        try:
            payload = json.dumps({
                "tool": "event_ingest",
                "agent_id": "browser",
                "params": {"source": "browser", "url": url, "title": title, "content": body_text, "cookies": json.loads(cookies_json)},
            }).encode("utf-8")
            req = urllib.request.Request(
                "http://localhost:8000/v1/ingest",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=5):
                if self._win:
                    self._win.evaluate_js("document.getElementById('_kasa_status').innerText = 'ingested';")
                    self._win.evaluate_js("document.getElementById('_kasa_status').style.color = '#a6e3a1';")
                print(f"[KASA] ingested: {title}")
        except Exception as e:
            if self._win:
                self._win.evaluate_js("document.getElementById('_kasa_status').innerText = '!';")
                self._win.evaluate_js("document.getElementById('_kasa_status').style.color = '#f38ba8';")
            print(f"[KASA] ingest error: {e}")

    def show_status(self, message, color):
        if self._win:
            js = f"document.getElementById('_kasa_status').innerText = '{message}';"
            js += f"document.getElementById('_kasa_status').style.color = '{color}';"
            self._win.evaluate_js(js)


def open_browser(url: str = "https://lite.duckduckgo.com/lite"):
    api = KasaApi()
    win = webview.create_window("KASA Browser", url, js_api=api, width=1280, height=860)
    api.set_window(win)

    def on_loaded():
        win.evaluate_js(_TOOLBAR_JS)
        win.evaluate_js(_INGEST_JS)

    win.events.loaded += on_loaded
    webview.start()


if __name__ == "__main__":
    open_browser()