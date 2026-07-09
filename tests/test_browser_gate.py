# -*- coding: utf-8 -*-
"""browser_gate.evaluate() icin saf-mantik regresyon testi (GUI gerektirmez)."""
import importlib.util
import os

REPO = "d:/kasa"
GATE_PATH = os.path.join(REPO, "_orch/loop/browser_gate.py")


def _load_gate():
    spec = importlib.util.spec_from_file_location("browser_gate", GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_evaluate_clean_record_ok():
    gate = _load_gate()
    records = [{
        "pass": 2,
        "http": {"accept_language": "de-DE,de;q=0.9"},
        "js": {
            "language": "de-DE",
            "webglRenderer": "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "timezone": "Europe/Berlin",
            "tzOffset": -120,
            "platform": "Win32",
        },
    }]
    ok, report = gate.evaluate(records)
    assert ok is True
    assert report["boot_ok"] is True
    assert report["leaks"] == []


def test_evaluate_leaky_record_detected():
    gate = _load_gate()
    records = [{
        "pass": 2,
        "http": {"accept_language": "tr-TR,tr;q=0.9"},
        "js": {
            "language": "de-DE",
            "webglRenderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 5070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "timezone": "Europe/Berlin",
            "tzOffset": -60,
            "platform": "Win32",
        },
    }]
    ok, report = gate.evaluate(records)
    assert ok is False
    assert "webgl" in report["leaks"]
    assert "accept_language" in report["leaks"]


def test_evaluate_no_records_means_boot_failed():
    gate = _load_gate()
    ok, report = gate.evaluate([])
    assert report["boot_ok"] is False
    assert ok is False
