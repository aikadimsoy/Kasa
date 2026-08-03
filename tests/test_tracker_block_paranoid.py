# -*- coding: utf-8 -*-
"""Paranoid seviyede bilinen tracker isteklerinin engellenmesi (su ana kadar sadece etikette vaat ediliyordu)."""
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


def test_tracker_domain_blocklist_present():
    src = _read()
    assert "KASA_TRACKER_DOMAINS" in src


def test_fetch_and_xhr_patched_for_blocking():
    src = _read()
    assert "fetch" in src.split("KASA_TRACKER_DOMAINS", 1)[-1][:3000]
    assert "XMLHttpRequest.prototype.open" in src


def test_gated_on_paranoid_only():
    src = _read()
    start = src.find("KASA_TRACKER_DOMAINS")
    assert start != -1
    nearby = src[max(0, start - 200):start + 2000]
    assert "paranoid" in nearby.lower(), (
        "Tracker istek engelleme SADECE paranoid seviyede aktif olmali "
        "(strict/standard davranisi degismemeli)"
    )


def test_existing_privacy_injection_untouched():
    src = _read()
    assert "_PRIVACY_JS" in src
    assert "_kp_canvas_seed" in src
    assert "POISON" in src
