# -*- coding: utf-8 -*-
"""browser_window.py saglik-kancasi + mevcut gizlilik enjeksiyonlarinin bozulmadigini dogrular."""
import os

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
BROWSER_FILE = os.path.join(_KASA_ROOT, "src/browser/browser_window.py")


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
