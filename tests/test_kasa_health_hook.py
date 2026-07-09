# -*- coding: utf-8 -*-
"""browser_window.py saglik-kancasi + mevcut gizlilik enjeksiyonlarinin bozulmadigini dogrular."""
import os

BROWSER_FILE = os.path.join("d:/kasa", "src/browser/browser_window.py")


def _read():
    with open(BROWSER_FILE, encoding="utf-8") as f:
        return f.read()


def test_headless_health_env_hook_present():
    src = _read()
    assert "KASA_HEALTHCHECK_URL" in src
    assert "win.destroy" in src


def test_debug_devtools_mode_preserved():
    assert "webview.start(debug=True)" in _read()


def test_privacy_injection_preserved():
    src = _read()
    assert "_register_early_privacy" in src
    assert "_PRIVACY_JS" in src
