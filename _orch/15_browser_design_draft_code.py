```python
import webview
import urllib.request
import json
import threading
import os

# KASA toolbar — her sayfaya enjekte edilir
_TOOLBAR_JS = r"""
(function() {
    if (document.getElementById('_kasa_toolbar')) return;

    // Chromium tarzı URL/arama heuristic
    window._kasa_navigate = function(v) {
        v = (v || '').trim();
        if (!v) return;
        // Protokol varsa direkt git
        if (/^[a-z][a-z0-9+.\-]*:\/\//i.test(v)) {
            window.location.href = v;
            return;
        }
        // Boşluk yok + domain pattern → https ekle
        if (!/\s/.test(v) && /^[a-z0-9]([a-z0-9\-]*\.)+[a-z]{2,}(\/.*)?$/i.test(v)) {
            window.location.href = 'https://' + v;
            return;
        }
        // Aksi hâlde DuckDuckGo araması
        window.location.href = 'https://lite.duckduckgo.com/lite?q=' + encodeURIComponent(v);
    };

    // target="_blank" linkleri yeni sekme yerine aynı pencerede aç
    document.addEventListener('click', function(e) {
        var a = e.target.closest('a');
        if (a && a.target === '_blank' && a.href) {
            e.preventDefault();
            e.stopPropagation();
            window.location.href = a.href;
        }
    }, true);

    // Toolbar oluştur
    var bar = document.createElement('div');
    bar.id = '_kasa_toolbar';
    bar.style.cssText = [
        'position:fixed', 'top:0', 'left:0', 'right:0', 'height:48px',
        'background:var(--kasa-n950)', 'display:flex', 'align-items:center',
        'gap:8px', 'padding:0 12px', 'z-index:2147483647',
        'font-family:\'KasaUI\', sans-serif', 'font-size:13px',
        'box-shadow:var(--kasa-e2)',
    ].join(';');

    var btnStyle = 'color:white;background:var(--kasa-n800);border:none;border-radius:4px;padding:6px 12px;cursor:pointer;';
    bar.innerHTML =
        '<button style="' + btnStyle + '" onclick="history.go(-1)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M3 12L12 4l9 8"/></button>' +
        '<button style="' + btnStyle + '" onclick="history.go(1)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M19 6L13 12l6 6"/></button>' +
        '<button style="' + btnStyle + '" onclick="location.reload()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M6 4h13"/></button>' +
        '<div style="display:flex;flex:1;height:36px;background:var(--kasa-n800);border:1px solid var(--kasa-n700);border-radius:9999px;align-items:center;gap:8px;padding:0 12px;">' +
            '<div id="security_ring" style="position:relative;">' +
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>' +
                '<div id="security_status" style="position:absolute;top:2px;right:-6px;width:8px;height:8px;border-radius:50%;background:var(--kasa-n300);"></div>' +
            '</div>' +
            '<input id="_kasa_url" type="text" value="' + window.location.href.replace(/"/g, '&quot;') + '" style="flex:1;background:transparent;color:white;border:none;outline:none;">' +
        '</div>' +
        '<span id="_kasa_status" style="color:var(--kasa-n500);font-size:11px;margin-left:auto;">KASA</span>';

    document.body.style.marginTop = '48px';
    document.body.insertBefore(bar, document.body.firstChild);

    // URL pollıng
    var lastUrl = window.location.href;
    setInterval(function() {
        if (lastUrl !== window.location.href) {
            lastUrl = window.location.href;
            document.getElementById('_kasa_url').value = lastUrl;
            updateSecurityRing();
        }
    }, 500);

    function updateSecurityRing() {
        var protocol = window.location.protocol;
        var securityIcon = document.getElementById('security_ring');
        if (protocol === 'https:') {
            securityIcon.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9,12 11,14 15,10"/></svg>';
            securityIcon.style.color = 'var(--kasa-secure)';
        } else if (protocol === 'http:') {
            securityIcon.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="9" y1="9" x2="15" y2="15"/></line><line x1="15" y1="9" x2="9" y2="15"/></svg>';
            securityIcon.style.color = 'var(--kasa-danger)';
        } else {
            securityIcon.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="9" x2="12" y2="13"/><dot cx="12" cy="16" r="0.5" fill="currentColor"/></svg>';
            securityIcon.style.color = 'var(--kasa-warning)';
        }
    }
})();
"""

_INGEST_JS = """
(function() {
    var url = window.location.href;
    var title = document.title;
    var body = (document.body ? document.body.innerText : '').substring(0, 3000);
    var cookies = document.cookie.split(';').map(function(c) {
        var parts = c.trim().split('=');
        return { name: parts[0], value: parts.slice(1).join('=') };
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
                "params": {
                    "source": "browser",
                    "type": "page_visit",
                    "content": {
                        "url": url,
                        "title": title,
                        "text": body_text,
                        "cookies":