# -*- coding: utf-8 -*-
"""B1 about:blank-bootstrap cekirdek mantik regresyonu (Controller, ilke-7).
GUI GEREKTIRMEZ: saf fonksiyonlar + sahte-core ile sira/fail-safe/idempotency/watchdog
degismezlerini deterministik dogrular. Canli CoreWebView2 sira-davranisi AYRI kapi (Kapi-2)."""
import sys

sys.path.insert(0, "d:/kasa")
import src.browser.browser_window as bw


class _FakeCore:
    """CLR-bagimsiz core arayuzunu taklit eder; tum cagrilari paylasilan 'log'a yazar.
    defer=True -> when_all cb'yi HEMEN cagirmaz, saklar (fire() ile tetiklenir).
    raise_on_add=True -> add_script patlar (fail-safe yolunu test icin)."""

    def __init__(self, log, defer=False, raise_on_add=False):
        self.log = log
        self.defer = defer
        self.raise_on_add = raise_on_add
        self._pending = None

    def set_tracking(self, level):
        self.log.append(("tracking", level))

    def add_script(self, js):
        if self.raise_on_add:
            raise RuntimeError("add_script boom")
        self.log.append(("add", js))
        return ("task", js)

    def when_all(self, tasks, cb):
        self.log.append(("when_all", len(tasks)))
        if self.defer:
            self._pending = cb
        else:
            cb()

    def fire(self):
        if self._pending:
            self._pending()
            self._pending = None


def test_scripts_registered_before_navigate():
    # DEGISMEZ: tracking -> add(prelude) -> add(privacy) -> navigate. Navigate en sonda.
    log = []
    core = _FakeCore(log)
    navigate = lambda u: log.append(("navigate", u))
    bw._bootstrap_privacy_navigation(core, navigate, "http://real", "PRE", "PRIV")
    assert log == [
        ("tracking", 1),
        ("add", "PRE"),
        ("add", "PRIV"),
        ("when_all", 2),
        ("navigate", "http://real"),
    ]


def test_navigate_gated_on_when_all_not_eager():
    # Navigate ASLA eager degil: when_all cozulene kadar cagrilmaz (yaris onleme).
    log = []
    core = _FakeCore(log, defer=True)
    navigate = lambda u: log.append(("navigate", u))
    bw._bootstrap_privacy_navigation(core, navigate, "http://real", "PRE", "PRIV")
    assert ("navigate", "http://real") not in log      # henuz YOK
    core.fire()                                          # her iki kayit cozuldu
    assert log[-1] == ("navigate", "http://real")        # simdi navigate


def test_failsafe_navigates_on_exception():
    # FAIL-SAFE (taban=bugun): kayit patlarsa yine de gercek url'e git.
    log = []
    core = _FakeCore(log, raise_on_add=True)
    navigate = lambda u: log.append(("navigate", u))
    bw._bootstrap_privacy_navigation(core, navigate, "http://real", "PRE", "PRIV")
    assert ("navigate", "http://real") in log


def test_navigate_once_is_idempotent():
    # bootstrap-continuation VE watchdog ayni anda tetiklense bile load_url TEK KEZ.
    loads = []
    navigate = bw._make_navigate_once(lambda u: loads.append(u))
    assert navigate("http://real") is True
    assert navigate("http://real") is False
    assert navigate("http://other") is False
    assert loads == ["http://real"]
    assert navigate.done() is True


def test_navigate_once_starts_not_done():
    navigate = bw._make_navigate_once(lambda u: None)
    assert navigate.done() is False


def test_watchdog_only_navigates_when_not_navigated():
    assert bw._watchdog_should_navigate(False) is True    # navigasyon yok -> fallback sart
    assert bw._watchdog_should_navigate(True) is False     # zaten navigasyon var -> dokunma
