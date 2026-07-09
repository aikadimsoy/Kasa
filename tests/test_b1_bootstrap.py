# -*- coding: utf-8 -*-
"""B1 inline-html bootstrap cekirdek mantik regresyonu (Controller, ilke-7).
GUI GEREKTIRMEZ: saf fonksiyonlar + sahte-core ile deterministik-sira / fail-safe / fail-audible /
idempotency / navigate-rollback / watchdog degismezlerini dogrular. Canli CoreWebView2 ContinueWith
davranisi AYRI kapi (Kapi-2)."""
import os
import sys
import tempfile

sys.path.insert(0, "d:/kasa")
import src.browser.browser_window as bw


class _FakeCore:
    """CLR-bagimsiz core arayuzunu taklit eder; tum cagrilari paylasilan 'log'a yazar.
    defer=True -> when_ready cb'yi HEMEN cagirmaz, saklar (fire() ile tetiklenir) — ContinueWith'in
    kayit-tamamlanmasini bekledigini modellemek icin. raise_on_add=True -> add_script patlar."""

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

    def when_ready(self, task, cb):
        self.log.append(("when_ready",))
        if self.defer:
            self._pending = cb
        else:
            cb()

    def fire(self):
        if self._pending:
            self._pending()
            self._pending = None


def test_script_registered_before_navigate():
    # DEGISMEZ: tracking -> add(early_js) -> when_ready -> navigate. Navigate en sonda.
    log = []
    core = _FakeCore(log)
    navigate = lambda u: log.append(("navigate", u))
    bw._bootstrap_privacy_navigation(core, navigate, "http://real", "EARLY", on_fallback=None)
    assert log == [
        ("tracking", 1),
        ("add", "EARLY"),
        ("when_ready",),
        ("navigate", "http://real"),
    ]


def test_navigate_gated_on_when_ready_not_eager():
    # Navigate ASLA eager degil: kayit TAMAMLANANA (when_ready cb) kadar cagrilmaz -> yaris yok.
    log = []
    core = _FakeCore(log, defer=True)
    navigate = lambda u: log.append(("navigate", u))
    bw._bootstrap_privacy_navigation(core, navigate, "http://real", "EARLY")
    assert ("navigate", "http://real") not in log       # henuz YOK (kayit beklemede)
    core.fire()                                          # kayit tamamlandi
    assert log[-1] == ("navigate", "http://real")        # simdi navigate


def test_failsafe_navigates_and_audits_on_exception():
    # FAIL-SAFE + FAIL-AUDIBLE: kayit patlarsa on_fallback(reason) + yine de gercek url'e git.
    log = []
    audits = []
    core = _FakeCore(log, raise_on_add=True)
    navigate = lambda u: log.append(("navigate", u))
    bw._bootstrap_privacy_navigation(core, navigate, "http://real", "EARLY", on_fallback=audits.append)
    assert ("navigate", "http://real") in log            # taban navigasyon yapildi
    assert audits and audits[0].startswith("bootstrap_exception")  # SESSIZ degil: denetlenebilir


def test_navigate_once_is_idempotent():
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


def test_navigate_once_rolls_back_on_load_error_and_can_retry():
    # ASILI-BLANK REGRESYONU: load_url ~20s'te WebViewException firlatirsa done GERI ALINIR ve
    # yeniden deneme mumkun olur (aksi halde pencere blank'te asili kalirdi).
    calls = {"n": 0}
    errs = []

    def flaky(url):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("shown timeout")   # ilk deneme (yavas WebView2 init)

    navigate = bw._make_navigate_once(flaky, on_error=errs.append)
    assert navigate("http://real") is False        # ilk deneme patladi
    assert navigate.done() is False                # done GERI ALINDI
    assert errs and errs[0].startswith("navigate_load_url_failed")  # denetlenebilir
    assert navigate("http://real") is True         # ikinci deneme basarili
    assert navigate.done() is True
    assert calls["n"] == 2


def test_watchdog_only_navigates_when_not_navigated():
    assert bw._watchdog_should_navigate(False) is True     # navigasyon yok -> fallback sart
    assert bw._watchdog_should_navigate(True) is False      # zaten navigasyon var -> dokunma


def test_audit_b1_writes_auditable_event(monkeypatch):
    # FAIL-AUDIBLE kaydin GERCEKTEN diske dustugunu dogrula (sessiz fail-open olmadigi kaniti).
    tmp = os.path.join(tempfile.mkdtemp(), "b1_events.log")
    monkeypatch.setattr(bw, "_B1_EVENT_LOG", tmp)
    bw._audit_b1("test_reason_xyz")
    with open(tmp, encoding="utf-8") as f:
        line = f.read()
    assert "b1_protection_fallback" in line and "test_reason_xyz" in line
