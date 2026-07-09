# -*- coding: utf-8 -*-
"""B1 inline-html bootstrap + COLD FAIL-CLOSED cekirdek mantik regresyonu (Controller, ilke-7).
GUI GEREKTIRMEZ: saf fonksiyonlar + sahte-core ile deterministik-sira / no-fail-open / retry-injection
/ fail-closed / idempotency / navigate-rollback / watchdog-fail-closed / fail-audible dogrulanir.
Canli CoreWebView2 ContinueWith davranisi AYRI kapi (Kapi-2)."""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, "d:/kasa")
import src.browser.browser_window as bw


class _FakeCore:
    """CLR-bagimsiz core arayuzu; cagrilari paylasilan 'log'a yazar. defer=True -> when_ready cb'yi
    saklar (fire() ile). raise_on_add=True -> add_script patlar (kayit-hatasi yolu)."""

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


# ---- cekirdek gate: deterministik sira + FAIL-OPEN YOK ----

def test_script_registered_before_navigate():
    log = []
    core = _FakeCore(log)
    navigate = lambda u: log.append(("navigate", u))
    bw._bootstrap_privacy_navigation(core, navigate, "http://real", "EARLY")
    assert log == [("tracking", 1), ("add", "EARLY"), ("when_ready",), ("navigate", "http://real")]


def test_navigate_gated_on_when_ready_not_eager():
    log = []
    core = _FakeCore(log, defer=True)
    navigate = lambda u: log.append(("navigate", u))
    bw._bootstrap_privacy_navigation(core, navigate, "http://real", "EARLY")
    assert ("navigate", "http://real") not in log   # kayit beklemede -> navigate YOK
    core.fire()
    assert log[-1] == ("navigate", "http://real")


def test_bootstrap_raises_and_never_navigates_on_failure():
    # FAIL-OPEN YOK: kayit patlarsa EXCEPTION yukari verilir, navigate ASLA cagrilmaz.
    log = []
    core = _FakeCore(log, raise_on_add=True)
    navigate = lambda u: log.append(("navigate", u))
    with pytest.raises(Exception):
        bw._bootstrap_privacy_navigation(core, navigate, "http://real", "EARLY")
    assert ("navigate", "http://real") not in log


# ---- idempotent navigate + rollback ----

def test_navigate_once_is_idempotent():
    loads = []
    navigate = bw._make_navigate_once(lambda u: loads.append(u))
    assert navigate("http://real") is True
    assert navigate("http://real") is False
    assert loads == ["http://real"]
    assert navigate.done() is True


def test_navigate_once_starts_not_done():
    assert bw._make_navigate_once(lambda u: None).done() is False


def test_navigate_once_rolls_back_on_load_error_and_can_retry():
    calls = {"n": 0}
    errs = []

    def flaky(url):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("shown timeout")

    navigate = bw._make_navigate_once(flaky, on_error=errs.append)
    assert navigate("http://real") is False
    assert navigate.done() is False
    assert errs and errs[0].startswith("navigate_load_url_failed")
    assert navigate("http://real") is True
    assert navigate.done() is True
    assert calls["n"] == 2


# ---- COLD FAIL-CLOSED: retry ENJEKSIYONU (navigasyonu degil), tutmazsa inert ----

def test_inject_retry_succeeds_after_transient_core_failure():
    attempts = {"core": 0}
    registered = []
    errors = []

    def get_core():
        attempts["core"] += 1
        if attempts["core"] < 2:
            raise RuntimeError("CoreWebView2 hazir degil")
        return "CORE"

    ok = bw._inject_with_retry(get_core, registered.append, lambda: errors.append("err"), max_attempts=3)
    assert ok is True and registered == ["CORE"] and errors == []


def test_inject_retry_fail_closed_never_registers_or_navigates():
    registered = []
    errors = []
    ok = bw._inject_with_retry(
        lambda: (_ for _ in ()).throw(RuntimeError("hic hazir olmadi")),
        registered.append, lambda: errors.append("err"), max_attempts=3)
    assert ok is False and registered == [] and errors == ["err"]  # FAIL-CLOSED: kayit/nav YOK


def test_inject_retry_retries_injection_not_navigation():
    # register (add_script) patlarsa navigate CAGRILMAMALI; retry register'i tekrar dener.
    reg = {"n": 0}
    navigated = []

    def register(core):
        reg["n"] += 1
        if reg["n"] < 2:
            raise RuntimeError("add_script fail")
        navigated.append(core)  # ancak basarili kayitta 'navigate' (burada temsili)

    ok = bw._inject_with_retry(lambda: "CORE", register, lambda: None, max_attempts=3)
    assert ok is True and navigated == ["CORE"] and reg["n"] == 2


# ---- watchdog FAIL-CLOSED uyumlu (fail-open'a cevirmez) ----

def test_watchdog_action_noop_when_navigated():
    assert bw._watchdog_action(True, False) == "noop"
    assert bw._watchdog_action(True, True) == "noop"


def test_watchdog_action_navigate_when_registered_but_not_navigated():
    assert bw._watchdog_action(False, True) == "navigate"


def test_watchdog_action_failclosed_when_no_registration():
    # Kayit YOK + nav YOK -> 'failclosed' (enjeksiyonsuz real'e GITME, fail-open geri uretme).
    assert bw._watchdog_action(False, False) == "failclosed"


# ---- inert hata: navigasyon/localhost yok, sadece mevcut dokumana JS ----

def test_show_inert_error_uses_evaluate_js_no_navigation():
    calls = {"eval": [], "load": []}

    class _FakeWin:
        def evaluate_js(self, js):
            calls["eval"].append(js)

        def load_url(self, url):
            calls["load"].append(url)   # CAGRILMAMALI

    bw._show_inert_error(_FakeWin())
    assert calls["load"] == []                         # navigasyon YOK
    assert calls["eval"] and "innerHTML" in calls["eval"][0]  # sadece mevcut dokumana yazdi


# ---- fail-audible ----

def test_audit_b1_writes_auditable_event(monkeypatch):
    tmp = os.path.join(tempfile.mkdtemp(), "b1_events.log")
    monkeypatch.setattr(bw, "_B1_EVENT_LOG", tmp)
    bw._audit_b1("test_reason_xyz")
    with open(tmp, encoding="utf-8") as f:
        line = f.read()
    assert "b1_protection_fallback" in line and "test_reason_xyz" in line
