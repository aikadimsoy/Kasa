# -*- coding: utf-8 -*-
"""B1 muhur kapisi testleri. Port-probe GERCEK http.server'a karsi (mock DEGIL, gercek soket) ->
'kod-hakkinda-inanc degil ampirik' ilkesini bu testin kendisi uygular. seal_decision saf kapi."""
import functools
import http.server
import os
import sys
import tempfile
import threading

sys.path.insert(0, "d:/kasa")
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
