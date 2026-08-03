# -*- coding: utf-8 -*-
"""Regression guards for the experimental browser surface (src/browser).

Two independent defects are pinned here.

1. OPT-IN GATE. The browser must stay off unless the operator explicitly asks
   for it, and it must fail closed BEFORE any side effect -- no proxy env
   mutation, no window, no js_api bridge.
   Rationale: the pywebview js_api bridge lives in the *visited page's* JS
   context, and the toolbar/sidebar/ingest scripts are injected on every load
   with no origin check. Any visited site can therefore reach
   window.pywebview.api.* directly. See SECURITY.md, "Known-unsafe surfaces".

2. ADDRESS BAR. The URL must never be interpolated into an HTML string. The
   previous code escaped only `"` and left `&` untouched -- the classic
   double-decoding hole: a URL carrying the literal text `&quot;` never trips
   the escape, then the HTML parser decodes it back into `"` and the attribute
   is broken out of.

Turkce not: 2. grup bir "somuru var mi" testi DEGIL, bir DESEN testidir. Calisan
bir somuru yazip olcmedik -- o WebView2'nin URL normalizasyonuna bagli ve
olculmedi, dolayisiyla "sizinti yok" diyemeyiz. Bunun yerine hatanin SINIFINI
geri gelemez kiliyoruz: kaynakta interpolasyon deseni yeniden belirirse test
kirilir. Olculmemis bir iddiada bulunmadan kalici koruma saglamanin yolu budur.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.browser import browser_window as bw  # noqa: E402


# --- 1. Opt-in gate ---------------------------------------------------------

@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " 1 "])
def test_gate_opens_only_for_explicit_optin(monkeypatch, value):
    monkeypatch.setenv(bw.BROWSER_ENABLE_ENV, value)
    assert bw.browser_enabled() is True


@pytest.mark.parametrize("value", ["", "0", "no", "off", "false", "maybe"])
def test_gate_stays_closed_for_everything_else(monkeypatch, value):
    monkeypatch.setenv(bw.BROWSER_ENABLE_ENV, value)
    assert bw.browser_enabled() is False


def test_gate_closed_when_env_absent(monkeypatch):
    monkeypatch.delenv(bw.BROWSER_ENABLE_ENV, raising=False)
    assert bw.browser_enabled() is False


def test_open_browser_refuses_when_disabled(monkeypatch):
    monkeypatch.delenv(bw.BROWSER_ENABLE_ENV, raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        bw.open_browser()
    # The refusal has to be actionable: it must name the switch.
    assert bw.BROWSER_ENABLE_ENV in str(excinfo.value)


def test_open_browser_fails_closed_before_any_side_effect(monkeypatch):
    """Refusal must precede proxy setup and window creation.

    Turkce not: "kapali" demek "acilip sonra kapanmak" degildir. Kapi fonksiyonun
    ilk satirindan asagi kayarsa bu test kirilir -- cunku o durumda
    _apply_proxy_env surec ortamini coktan degistirmis, create_window ise
    kopruyu coktan kurmus olurdu.
    """
    monkeypatch.delenv(bw.BROWSER_ENABLE_ENV, raising=False)
    tripped = []

    monkeypatch.setattr(bw, "_apply_proxy_env",
                        lambda *a, **k: tripped.append("_apply_proxy_env"))
    monkeypatch.setattr(bw.webview, "create_window",
                        lambda *a, **k: tripped.append("create_window"))

    with pytest.raises(RuntimeError):
        bw.open_browser()

    assert tripped == [], f"side effects ran before the gate: {tripped}"


def test_gate_actually_lets_an_opted_in_run_through(monkeypatch):
    """Positive control: the gate must not be a blanket refusal.

    Turkce not: bir kapinin "reddediyor" testi tek basina degersizdir -- her zaman
    reddeden bir kapi da o testi gecer. Burada tersini olcuyoruz: opt-in verilince
    calisma AKISI kapinin otesine geciyor mu? create_window'u sentinel ile
    degistirip ona ULASILDIGINI dogruluyoruz. Boylece test "hep reddet" ile
    "dogru kosulda gecir" arasini ayirt eder (pozitif + negatif kontrol cifti).
    """
    monkeypatch.setenv(bw.BROWSER_ENABLE_ENV, "1")

    class _ReachedWindowCreation(Exception):
        pass

    monkeypatch.setattr(bw, "_apply_proxy_env", lambda *a, **k: None)

    def _sentinel(*a, **k):
        raise _ReachedWindowCreation

    monkeypatch.setattr(bw.webview, "create_window", _sentinel)

    # Reaching create_window proves the gate opened; we stop there so no real
    # window (and no js_api bridge) is ever built during the test run.
    with pytest.raises(_ReachedWindowCreation):
        bw.open_browser()


# --- 2. Address bar must not interpolate the URL into HTML ------------------

def _code_only(js: str) -> str:
    """Drop whole-line // comments so these checks judge code, not prose.

    Turkce not: yalniz ilk anlamli karakteri // olan SATIRLAR atilir. Satir-ici
    kirpma yapmiyoruz, cunku o "https://" gibi gercek kod parcalarini da keser ve
    test gercek bir ihlali gormezden gelebilirdi. Burada amac testi gevsetmek
    degil, hedefini daraltmak: aciklama yazisi ihlal sayilmasin, kod sayilsin.
    """
    return "\n".join(
        line for line in js.splitlines() if not line.lstrip().startswith("//")
    )


def test_toolbar_does_not_interpolate_url_into_html():
    js = _code_only(bw._TOOLBAR_JS)
    assert "value=\"' +" not in js, "URL is interpolated into an HTML attribute again"
    assert "location.href.replace" not in js, "hand-rolled URL escaping is back"


def test_toolbar_seeds_url_via_dom_property():
    js = _code_only(bw._TOOLBAR_JS)
    assert "_urlInp.value = window.location.href" in js, \
        "address bar no longer seeds its value via the DOM property"


def test_url_input_markup_carries_no_value_attribute():
    js = _code_only(bw._TOOLBAR_JS)
    start = js.index('<input id="_kasa_url"')
    element = js[start:start + 400]   # the element's own markup, not the whole toolbar
    assert " value=" not in element, "value= attribute reintroduced on the URL input"
