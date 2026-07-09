import webview
import urllib.request
import json
import threading
import os
import sys

class KasaApi:
    def __init__(self):
        self.token = os.getenv('KASA_BEARER_TOKEN', '')

    def ingest(self, url, title, body_text):
        data = {
            "tool": "event_ingest",
            "agent_id": "browser",
            "params": {"source": "browser", "url": url, "title": title, "content": body_text}
        }
        data_json = json.dumps(data).encode('utf-8')
        req = urllib.request.Request("http://localhost:8000/v1/ingest", data=data_json, headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                print(f"[KASA] ingested: {title}")
        except Exception as e:
            print(f"[KASA] ingest error: {e}")

def on_loaded():
    window.evaluate_js("""
        (function(){
            var url = window.location.href;
            var title = document.title;
            var body = (document.body ? document.body.innerText : '').substring(0, 3000);
            window.pywebview.api.ingest(url, title, body);
        })();
    """)

def open_browser(url=None):
    if url is None:
        url = "https://lite.duckduckgo.com/lite"
    
    api = KasaApi()
    api_obj = webview.JsApi(api)
    
    window = webview.create_window("KASA Browser", url, js_api=api_obj, width=1200, height=800)
    window.events.loaded += on_loaded

    toolbar_html = """
        <div style="position: fixed; top: 0; left: 0; background: white; z-index: 9999;">
            <button onclick="window.history.go(-1)">Back</button>
            <button onclick="window.history.go(1)">Forward</button>
            <button onclick="location.reload()">Reload</button>
            <input type="text" id="urlInput" placeholder="Enter URL">
            <button onclick="window.location.href = document.getElementById('urlInput').value;">Go</button>
        </div>
    """
    
    window.evaluate_js("document.body.innerHTML += arguments[0];", toolbar_html)
    
    webview.start(func=None, args=())

if __name__ == "__main__":
    open_browser()