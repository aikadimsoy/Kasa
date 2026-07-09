# -*- coding: utf-8 -*-
"""
L4 TOCTOU / owner-gate KALICI regresyon (Controller, plan §2 ilke 9).
paranoid (agresif/site-kirabilen) kademe yalniz owner-sifresiyle ACIK oturumda gecerli olmali.
Kanit: (1) set_level gate kilitliyken reddeder; (2) EYLEM NOKTASINDA (boot) config dogrudan
'paranoid'e kurcalanmis olsa bile strict'e dusurur -> gate yalniz set_level'da degil, yuklemede de.
"""
import sys
import os
import json
import tempfile

sys.path.insert(0, "d:/kasa")
import src.browser.browser_window as bw


def _tmp_cfg(content):
    p = os.path.join(tempfile.mkdtemp(), "browser_config.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(content, f)
    return p


def test_set_level_paranoid_rejected_when_locked(monkeypatch):
    cfg = _tmp_cfg({"privacy_level": "strict"})
    monkeypatch.setattr(bw, "_BROWSER_CONFIG_PATH", cfg)
    api = bw.KasaApi()
    api._adv_unlocked = False
    res = api.set_level("paranoid")
    assert res != "paranoid", f"kilitliyken paranoid kabul edildi: {res}"
    assert json.load(open(cfg, encoding="utf-8"))["privacy_level"] != "paranoid"


def test_set_level_paranoid_allowed_when_unlocked(monkeypatch):
    cfg = _tmp_cfg({"privacy_level": "strict"})
    monkeypatch.setattr(bw, "_BROWSER_CONFIG_PATH", cfg)
    api = bw.KasaApi()
    api._adv_unlocked = True
    assert api.set_level("paranoid") == "paranoid"


def test_boot_downgrades_tampered_paranoid(monkeypatch):
    # TOCTOU / eylem-noktasi: config DOGRUDAN paranoid'e kurcalanmis (set_level bypass) ->
    # boot _adv_unlocked=False oldugundan strict'e dusurmeli.
    cfg = _tmp_cfg({"privacy_level": "paranoid"})
    monkeypatch.setattr(bw, "_BROWSER_CONFIG_PATH", cfg)
    bw.KasaApi()  # __init__ boot-downgrade
    assert json.load(open(cfg, encoding="utf-8"))["privacy_level"] == "strict", \
        "kurcalanmis paranoid boot'ta strict'e dusurulmedi (action-point gate ihlali)"
