# -*- coding: utf-8 -*-
"""B1 muhur kapisi testleri. Port-probe GERCEK http.server'a karsi (mock DEGIL, gercek soket) ->
'kod-hakkinda-inanc degil ampirik' ilkesini bu testin kendisi uygular. seal_decision saf kapi."""
import functools
import http.server
import os
import sys
import tempfile
import threading

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _KASA_ROOT)
from tools.security_bench import b1_seal


def _serve_dir(directory):
    """directory'yi gercek bir localhost HTTP sunucusu ile servis eder; (port, stop) doner."""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return port, httpd


# ---- (2) AMPIRIK probe: gercek soket, gercek HTTP ----

def test_serves_kasa_detects_real_file_server():
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "sentinel.txt"), "wb") as f:
        f.write(b"KASA_SEAL_SENTINEL_BYTES_0123456789")
    port, httpd = _serve_dir(d)
    try:
        # Sunucu sentinel'i servis ediyor -> probe TESPIT etmeli (acik ayakta olsaydi boyle gorunurdu)
        assert b1_seal._serves_kasa("127.0.0.1", port, "sentinel.txt",
                                    b"KASA_SEAL_SENTINEL_BYTES_0123456789") is True
    finally:
        httpd.shutdown()


def test_serves_kasa_clean_when_wrong_content():
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "sentinel.txt"), "wb") as f:
        f.write(b"tamamen farkli icerik")
    port, httpd = _serve_dir(d)
    try:
        assert b1_seal._serves_kasa("127.0.0.1", port, "sentinel.txt",
                                    b"KASA_SEAL_SENTINEL_BYTES_0123456789") is False
    finally:
        httpd.shutdown()


def test_serves_kasa_clean_when_no_listener():
    # Kapali/bos bir portta hicbir sey servis edilmiyor -> temiz (baglanti reddi).
    assert b1_seal._serves_kasa("127.0.0.1", 1, "sentinel.txt", b"x") is False


# ---- DETERMINISTIK muhur kapisi ----

def test_seal_only_when_all_three_green():
    status, reasons = b1_seal.seal_decision(True, True, True)
    assert status == "SEALED" and reasons == []


def test_seal_refused_if_cold_leaks():
    status, reasons = b1_seal.seal_decision(False, True, True)
    assert status == "NOT_SEALED" and "cold_pass1_leak" in reasons


def test_seal_refused_if_rogue_listener():
    status, reasons = b1_seal.seal_decision(True, False, True)
    assert status == "NOT_SEALED" and "rogue_localhost_server" in reasons


def test_seal_refused_if_watchdog_bad():
    status, reasons = b1_seal.seal_decision(True, True, False)
    assert status == "NOT_SEALED" and "watchdog_timing" in reasons


def test_seal_lists_every_red_signal():
    status, reasons = b1_seal.seal_decision(False, False, False)
    assert status == "NOT_SEALED"
    assert set(reasons) == {"cold_pass1_leak", "rogue_localhost_server", "watchdog_timing"}


# ---- NEGATIF KONTROL: unknown != PASS (ilke-11, muhur katmaninda) ----
# 'Mutlu yol' (uc yesil -> SEALED) yeterli DEGIL; asil risk 'olculemedi -> sahte-yesil'.

def test_seal_refused_when_signal_unmeasured_none():
    # Bir sinyal OLCULEMEDI (None) -> SEALED OLMAMALI, 'unmeasured' sebebi bildirilmeli.
    status, reasons = b1_seal.seal_decision(None, True, True)
    assert status == "NOT_SEALED" and "cold_pass1_unmeasured" in reasons


def test_seal_distinguishes_measured_red_from_unmeasured():
    # olculdu-kirmizi (False) ve olculemedi (None) AYRI raporlanir.
    status, reasons = b1_seal.seal_decision(False, None, True)
    assert status == "NOT_SEALED"
    assert "cold_pass1_leak" in reasons          # olculdu-kirmizi
    assert "rogue_probe_unmeasured" in reasons    # olculemedi


def test_seal_requires_strict_true_no_truthy_coercion():
    # Truthy-ama-True-degil (1, 'yes') PASS SAYILMAZ -> sahte-yesil deligi kapali.
    for bad in (1, "yes", [1], object()):
        status, reasons = b1_seal.seal_decision(bad, True, True)
        assert status == "NOT_SEALED", f"{bad!r} yanlislikla SEALED"
        assert "cold_pass1_unmeasured" in reasons


def test_rogue_signal_is_none_when_netstat_fails(monkeypatch):
    # AMPIRIK negatif kontrol: port-tarama patlarsa sinyal None (sahte-'temiz' DEGIL).
    def boom(*a, **k):
        raise RuntimeError("netstat patladi")
    monkeypatch.setattr(b1_seal, "_list_listening_ports", boom)
    assert b1_seal.rogue_listener_signal() is None


def test_rogue_signal_none_feeds_not_sealed(monkeypatch):
    # Uctan uca: netstat patlar -> no_rogue None -> seal_decision NOT_SEALED (unmeasured).
    monkeypatch.setattr(b1_seal, "_list_listening_ports",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    no_rogue = b1_seal.rogue_listener_signal()
    status, reasons = b1_seal.seal_decision(True, no_rogue, True)
    assert status == "NOT_SEALED" and "rogue_probe_unmeasured" in reasons


# ---- B3 DECOUPLE: accept_language (owner-gated) B1 muhrunu BATIRMAMALI ----

def test_b1_cold_excludes_b3_accept_language():
    assert b1_seal.b1_cold_from_meta(["webgl"]) == (False, False)
    # B3 acik (accept_language sizar) AMA B1 JS-katmani temiz -> b1_clean True, b3_open True
    assert b1_seal.b1_cold_from_meta(["accept_language"]) == (True, True)
    assert b1_seal.b1_cold_from_meta([]) == (True, False)
    assert b1_seal.b1_cold_from_meta(["timezone", "accept_language"]) == (False, True)


# ---- COLD DEDEKTOR KALIBRASYONU: alet kor ise (baseline sizmadi) sinyal None ----

def test_cold_signal_requires_calibrated_instrument():
    assert b1_seal.cold_signal_from_runs(True, True) is True      # ON temiz + baseline sizdi
    assert b1_seal.cold_signal_from_runs(False, True) is False     # ON kosum sizdi
    # Baseline (injection-off) SIZMADI -> alet KOR -> None (temiz-gorunen cold False-PASS olmasin)
    assert b1_seal.cold_signal_from_runs(True, False) is None
    assert b1_seal.cold_signal_from_runs(None, True) is None
    assert b1_seal.cold_signal_from_runs(True, None) is None


def test_blind_instrument_feeds_not_sealed():
    # Alet kor (baseline sizmadi) -> cold None -> seal_decision NOT_SEALED (cold_pass1_unmeasured).
    cold = b1_seal.cold_signal_from_runs(True, False)
    status, reasons = b1_seal.seal_decision(cold, True, True)
    assert status == "NOT_SEALED" and "cold_pass1_unmeasured" in reasons
