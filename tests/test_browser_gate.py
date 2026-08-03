# -*- coding: utf-8 -*-
"""browser_gate.evaluate() icin saf-mantik regresyon testi (GUI gerektirmez)."""
import importlib.util
import os

# Turkce not: sabit "d:/kasa" YERINE test dosyasinin kendi konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve CI
# kosucusunda bu testi kirardi; public yayin icin tasinabilirlik sart.
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
            # Sentetik GPU dizgesi (sahibin gercek kartini yazma): _GPU_MARKERS'a
            # takilir, known_spoofs'ta DEGILDIR -> "webgl" sizintisi beklenir.
            "webglRenderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
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


# --- B1 cold-session (pass==1) verdict testleri (ilke-7). GUI gerektirmez: sentetik
# --- captures ile evaluate_cold() mantigini dogrular. tzOffset dinamik hesaplanir
# --- (mevsimsel kirilganlik yok). Canli WebView2 kosumu AYRI kapi (Kapi-2).

def _clean_js(gate):
    return {
        "language": "de-DE",
        # spoof'lu/notr renderer: GPU belirteci (rtx/geforce/radeon/nvidia) YOK
        "webglRenderer": "ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device))",
        "timezone": "Europe/Berlin",
        "tzOffset": gate._berlin_expected_offset(),
        "platform": "Win32",
    }


def test_evaluate_cold_leaky_first_request_fails():
    # NEGATIF VAKA: spoof KAPALI, cold pass==1 gercek kimligi siziyor -> harness gormeli.
    gate = _load_gate()
    records = [{
        "pass": 1,
        "http": {"accept_language": "en-US,en;q=0.9"},
        "js": {
            "language": "en-US",
            "webglRenderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "timezone": "America/New_York",
            "tzOffset": 300,
            "platform": "Win32",
        },
    }]
    ok, meta = gate.evaluate_cold(records)
    assert ok is False
    assert meta["cold"] is True and meta["blind"] is False
    assert "webgl" in meta["leaks"] and "timezone" in meta["leaks"]


def test_evaluate_cold_clean_first_request_ok():
    # FAIL->PASS delta: spoof ACIK, cold pass==1'de tutarli kimlik -> sizinti yok.
    gate = _load_gate()
    records = [{
        "pass": 1,
        "http": {"accept_language": "de-DE,de;q=0.9"},
        "js": _clean_js(gate),
    }]
    ok, meta = gate.evaluate_cold(records)
    assert ok is True
    assert meta["leaks"] == [] and meta["blind"] is False


def test_evaluate_cold_no_cold_record_is_blind_not_pass():
    # FALSE-PASS AVI: sadece warmed pass==2 var, cold pass==1 YOK -> asla PASS deme.
    gate = _load_gate()
    records = [{"pass": 2, "http": {"accept_language": "de-DE,de;q=0.9"}, "js": _clean_js(gate)}]
    ok, meta = gate.evaluate_cold(records)
    assert ok is False
    assert meta["blind"] is True


def test_evaluate_cold_picks_earliest_pass1():
    # ILK istek semantigi: iki pass==1 varsa EN ERKEN olani (sizintili) secilir.
    gate = _load_gate()
    leaky = {
        "pass": 1, "http": {"accept_language": "en-US"},
        "js": {"language": "en-US", "webglRenderer": "NVIDIA GeForce RTX 4090",
               "timezone": "Europe/Berlin", "tzOffset": gate._berlin_expected_offset(),
               "platform": "Win32"},
    }
    clean = {"pass": 1, "http": {"accept_language": "de-DE,de;q=0.9"}, "js": _clean_js(gate)}
    ok, meta = gate.evaluate_cold([leaky, clean])
    assert ok is False                      # ilk (sizintili) kayit belirleyici
    assert "webgl" in meta["leaks"]


def test_cold_and_warmed_share_identical_rule():
    # ILKE-6: cold ve warmed AYNI _detect_leaks kuralini kullanir; kayit ayni ise
    # leak kumesi de ayni olmali (katman-tasima/kural-catallanmasi yok).
    gate = _load_gate()
    js = {"language": "de-DE", "webglRenderer": "Radeon RX 6800",
          "timezone": "Europe/Berlin", "tzOffset": gate._berlin_expected_offset(),
          "platform": "Win32"}
    http = {"accept_language": "de-DE,de;q=0.9"}
    _, cold_meta = gate.evaluate_cold([{"pass": 1, "http": http, "js": js}])
    _, warm_meta = gate.evaluate([{"pass": 2, "http": http, "js": js}])
    assert cold_meta["leaks"] == warm_meta["leaks"] == ["webgl"]
