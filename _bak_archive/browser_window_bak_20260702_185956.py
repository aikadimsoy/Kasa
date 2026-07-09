import webview
import urllib.request
import json
import threading
import os

# Design System v0.1 — CSS token tanımları ve self-host font yükleme
_DESIGN_CSS = r"""
@font-face {
    font-family: 'KasaUI';
    font-weight: 400;
    src: url('http://localhost:8000/assets/fonts/inter-400.woff2') format('woff2');
    font-display: swap;
}
@font-face {
    font-family: 'KasaUI';
    font-weight: 500;
    src: url('http://localhost:8000/assets/fonts/inter-500.woff2') format('woff2');
    font-display: swap;
}
@font-face {
    font-family: 'KasaUI';
    font-weight: 600;
    src: url('http://localhost:8000/assets/fonts/inter-600.woff2') format('woff2');
    font-display: swap;
}
@font-face {
    font-family: 'KasaMono';
    font-weight: 400;
    src: url('http://localhost:8000/assets/fonts/jetbrains-mono-400.woff2') format('woff2');
    font-display: swap;
}
:root {
    --kasa-primary:       #E02244;
    --kasa-primary-hover: #C41E3D;
    --kasa-accent:        #1BA7C2;
    --kasa-n950:          #0D1017;
    --kasa-n900:          #12161F;
    --kasa-n800:          #1A2029;
    --kasa-n700:          #242B37;
    --kasa-n500:          #5B6472;
    --kasa-n300:          #9AA3B2;
    --kasa-n100:          #E4E7EC;
    --kasa-secure:        #2FBF71;
    --kasa-warning:       #E8A13C;
    --kasa-danger:        #E5484D;
    --kasa-private:       #8B5CF6;
    --kasa-e1: 0 1px 2px rgba(0,0,0,.24);
    --kasa-e2: 0 4px 12px rgba(0,0,0,.32);
    --kasa-e3: 0 12px 32px rgba(0,0,0,.40);
    --kasa-t-micro: 120ms;
    --kasa-t-std:   200ms;
    --kasa-ease:    cubic-bezier(0.2,0,0,1);
}
#_kasa_toolbar button:hover {
    background: var(--kasa-n700) !important;
    transition: background var(--kasa-t-micro) var(--kasa-ease);
}
#_kasa_addr_box:focus-within {
    border-color: var(--kasa-accent) !important;
}
"""

# KASA toolbar — her sayfaya enjekte edilir
# deepseek/qwen taslağı; bug düzeltmeleri: CSS token enjeksiyonu, URL giriş handler,
# güvenlik halkası ID'leri, icon boyutları
_TOOLBAR_JS = r"""
(function() {
    if (document.getElementById('_kasa_toolbar')) return;

    // CSS token + font tanımlarını sayfaya enjekte et (var() referanslarından önce zorunlu)
    var _style = document.createElement('style');
    _style.textContent = window.__KASA_DESIGN_CSS__ || '';
    (document.head || document.documentElement).appendChild(_style);

    // Chromium tarzı URL/arama heuristic
    window._kasa_navigate = function(v) {
        v = (v || '').trim();
        if (!v) return;
        if (/^[a-z][a-z0-9+.\-]*:\/\//i.test(v)) {
            window.location.href = v;
            return;
        }
        if (!/\s/.test(v) && /^[a-z0-9]([a-z0-9\-]*\.)+[a-z]{2,}(\/.*)?$/i.test(v)) {
            window.location.href = 'https://' + v;
            return;
        }
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

    // Nav butonları: 48x48 dokunma hedefi (6x8), border-radius 12px (r-md)
    var btnStyle = [
        'color:var(--kasa-n300)',
        'background:transparent',
        'border:none',
        'border-radius:12px',
        'width:48px', 'height:48px',
        'display:flex', 'align-items:center', 'justify-content:center',
        'cursor:pointer', 'flex-shrink:0',
    ].join(';');

    var SVG_BACK   = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>';
    var SVG_FWD    = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>';
    var SVG_RELOAD = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.5 15a9 9 0 1 1-2.8-6.4L23 10"/></svg>';

    // Güvenlik halkası SVG'leri (24x24, outline)
    var SVG_SECURE  = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9,12 11,14 15,10"/></svg>';
    var SVG_DANGER  = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/></svg>';
    var SVG_WARNING = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="9" x2="12" y2="13"/><circle cx="12" cy="16" r="0.75" fill="currentColor"/></svg>';

    // Toolbar: 48px yukseklik (6x8), N-950 arkaplan
    var bar = document.createElement('div');
    bar.id = '_kasa_toolbar';
    bar.style.cssText = [
        'position:fixed', 'top:0', 'left:0', 'right:0', 'height:48px',
        'background:var(--kasa-n950)', 'display:flex', 'align-items:center',
        'gap:8px', 'padding:0 12px', 'z-index:2147483647',
        'font-family:KasaUI,system-ui,sans-serif', 'font-size:13px',
        'box-shadow:var(--kasa-e2)',
    ].join(';');

    // Adres cubugu: pill (r=9999), yukseklik 36px (4.5x8), KasaMono font
    bar.innerHTML =
        '<button id="_kb_back" style="' + btnStyle + '" onclick="history.go(-1)" title="Geri">' + SVG_BACK + '</button>' +
        '<button id="_kb_fwd"  style="' + btnStyle + '" onclick="history.go(1)"  title="Ileri">' + SVG_FWD + '</button>' +
        '<button id="_kb_rel"  style="' + btnStyle + '" onclick="location.reload()" title="Yenile">' + SVG_RELOAD + '</button>' +
        '<div id="_kasa_addr_box" style="display:flex;flex:1;height:36px;background:var(--kasa-n800);border:1px solid var(--kasa-n700);border-radius:9999px;align-items:center;gap:8px;padding:0 12px;min-width:0;">' +
            '<div id="_kasa_ring" style="flex-shrink:0;display:flex;color:var(--kasa-n300);">' + SVG_WARNING + '</div>' +
            '<input id="_kasa_url" type="text" autocomplete="off" spellcheck="false"' +
                ' value="' + window.location.href.replace(/"/g, '&quot;') + '"' +
                ' onkeydown="if(event.key===\'Enter\'){_kasa_navigate(this.value)}"' +
                ' style="flex:1;background:transparent;color:var(--kasa-n100);border:none;outline:none;font-family:KasaMono,monospace;font-size:14px;min-width:0;"' +
            '/>' +
            '<span id="_kasa_status" style="color:var(--kasa-n500);font-size:11px;flex-shrink:0;">KASA</span>' +
        '</div>';

    document.body.style.marginTop = '48px';
    document.body.insertBefore(bar, document.body.firstChild);

    // Guevenlik halkasini protokole gore guncelle
    function updateSecurityRing() {
        var ring = document.getElementById('_kasa_ring');
        if (!ring) return;
        var proto = window.location.protocol;
        if (proto === 'https:') {
            ring.innerHTML = SVG_SECURE;
            ring.style.color = 'var(--kasa-secure)';
            ring.title = 'Guvenli baglantr (HTTPS)';
        } else if (proto === 'http:') {
            ring.innerHTML = SVG_DANGER;
            ring.style.color = 'var(--kasa-danger)';
            ring.title = 'Guvensiz baglanti (HTTP)';
        } else {
            ring.innerHTML = SVG_WARNING;
            ring.style.color = 'var(--kasa-warning)';
            ring.title = 'Baglanti durumu bilinmiyor';
        }
    }

    // Adres cubugunu URL degisiminde guncelle (500ms polling)
    var _lastUrl = window.location.href;
    updateSecurityRing();
    setInterval(function() {
        if (_lastUrl !== window.location.href) {
            _lastUrl = window.location.href;
            var inp = document.getElementById('_kasa_url');
            // Kullanici yazarken guncelleme
            if (inp && document.activeElement !== inp) {
                inp.value = _lastUrl;
            }
            updateSecurityRing();
        }
    }, 500);
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
        threading.Thread(
            target=self._post,
            args=(url, title, body_text, cookies_json),
            daemon=True,
        ).start()

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
                        "cookies": json.loads(cookies_json),
                    },
                    "ttl_days": 30,
                },
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
                self._set_status("●", "#2FBF71")
                print(f"[KASA] ingested: {title}")
        except Exception as e:
            self._set_status("!", "#E5484D")
            print(f"[KASA] ingest error: {e}")

    def _set_status(self, message: str, color: str):
        if not self._win:
            return
        try:
            safe = message.replace("'", "\\'")
            self._win.evaluate_js(
                f"var s=document.getElementById('_kasa_status');"
                f"if(s){{s.innerText='{safe}';s.style.color='{color}';}}"
            )
        except Exception:
            pass

    def open_vault(self):
        print("[KASA] open_vault() cagridi — henuz uygulanmadi.")


def open_browser(url: str = "https://lite.duckduckgo.com/lite"):
    api = KasaApi()
    win = webview.create_window(
        "KASA Browser",
        url,
        js_api=api,
        width=1280,
        height=860,
    )
    api.set_window(win)

    def on_loaded():
        # CSS token'larini global degisken olarak yerlestir; toolbar JS okusun
        escaped = _DESIGN_CSS.replace("\\", "\\\\").replace("`", "\\`")
        win.evaluate_js(f"window.__KASA_DESIGN_CSS__ = `{escaped}`;")
        win.evaluate_js(_TOOLBAR_JS)
        win.evaluate_js(_INGEST_JS)

    win.events.loaded += on_loaded

    # Yeni pencere / sekme isteklerini ayni pencerede ac
    def on_new_window(event):
        try:
            target_url = event.url if hasattr(event, "url") else str(event)
            win.load_url(target_url)
        except Exception as e:
            print(f"[KASA] new_window_requested error: {e}")

    try:
        win.events.new_window_requested += on_new_window
    except AttributeError:
        pass  # Eski pywebview versiyonlarinda bu olay yoktur

    webview.start()


if __name__ == "__main__":
    open_browser()
