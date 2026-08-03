# -*- coding: utf-8 -*-
"""Davranissal B2 (WebGL/GPU) testi: gercek tarayiciyi acar, adversary_site'e yonlendirir
ve WebGL UNMASKED_RENDERER_WEBGL parametrelerinin tele (captures.jsonl) gercek GPU mu
yoksa spoof deger mi sizdirdigina bakar."""
import sys
import os

# kasa dizinini yola ekle ki importlar calissin
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from _orch.loop.browser_gate import run_gate

def test_webgl_behavioral_spoofing():
    # run_gate() KASA'yi baslatir ve 8901 portundaki adversary'e gonderir.
    # FLAKE FIX: full-suite yuku altinda gercek Chromium boot'u zaman zaman timeout'u asiyordu
    # (hata boot_ok'ta, leak'te DEGIL). Yalnizca BOOT flake'ini retry ile absorbe et; guvenlik
    # assertion'ini (leak) ASLA retry'lama -> gercek WebGL sizintisi sert bicimde kirmizi kalir.
    report = {}
    for _attempt in range(3):
        try:
            ok, report = run_gate(mode="fingerprint", timeout_s=20)
        except Exception as e:  # gecici boot/JS istisnasini absorbe et, kalici olan asagida patlar
            report = {"boot_ok": False, "error": repr(e)}
        if report.get("boot_ok") is True:
            break

    assert report.get("boot_ok") is True, f"Browser 3 denemede baslatilamadi: {report}"

    leaks = report.get("leaks", [])
    sample_renderer = report.get("sample", {}).get("js", {}).get("webglRenderer", "")

    assert "webgl" not in leaks, f"B2 (WebGL) acik! Gercek GPU tele dustu: {sample_renderer}"
