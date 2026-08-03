# kasa/tests/test_preflight.py

"""
Calisma-zamani bagimlilik on-kontrolu testleri.
Kritik invariant: tespit YEREL (ag yok); eksik bilesenin indirme URL'i RESMI Microsoft.
Simulate kancasi eksik-yolu deterministik test eder (gercekten eksik olmadan).
"""

import sys

import pytest

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _KASA_ROOT)

from src.desktop import preflight


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("KASA_PREFLIGHT_SIMULATE_MISSING", raising=False)
    yield


def test_simulate_missing_webview2(monkeypatch):
    monkeypatch.setenv("KASA_PREFLIGHT_SIMULATE_MISSING", "webview2")
    missing = preflight.missing_dependencies()
    keys = [d.key for d in missing]
    assert "webview2" in keys
    wv = next(d for d in missing if d.key == "webview2")
    assert wv.critical is True                      # WebView2 olmadan pencere acilmaz
    assert wv.url.startswith("https://")


def test_simulate_missing_both_critical_first(monkeypatch):
    monkeypatch.setenv("KASA_PREFLIGHT_SIMULATE_MISSING", "webview2,vcredist")
    missing = preflight.missing_dependencies()
    assert [d.key for d in missing] == ["webview2", "vcredist"]   # kritik once
    assert missing[0].critical is True
    assert missing[1].critical is False             # vcredist tavsiye niteligi


def test_download_urls_are_official_microsoft(monkeypatch):
    monkeypatch.setenv("KASA_PREFLIGHT_SIMULATE_MISSING", "webview2,vcredist")
    for d in preflight.missing_dependencies():
        assert d.url.startswith("https://")
        assert any(host in d.url for host in
                   ("microsoft.com", "aka.ms", "go.microsoft.com")), d.url


def test_detection_returns_bool():
    # Tespit fonksiyonlari her zaman bool doner (Windows disi = True; engelleme yok).
    assert isinstance(preflight.webview2_installed(), bool)
    assert isinstance(preflight.vcredist_installed(), bool)


@pytest.mark.skipif(sys.platform != "win32", reason="Registry tespiti Windows'a ozgu")
def test_no_simulate_all_present_or_reports():
    # Simulate yokken sonuc gercek makineye baglidir; ama donen her ogenin sema butunlugu
    # korunmali (ad + url + neden dolu).
    for d in preflight.missing_dependencies():
        assert d.name and d.reason and d.url
