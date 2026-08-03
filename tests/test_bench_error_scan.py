# -*- coding: utf-8 -*-
"""
Olcum butunlugu kapisi — URETICI tarafi (P0.1-B).

SEBEP: tools/security_bench/checks/scan.py, alet cevap uretemedigi DORT durumda da
'FAIL' basiyor: bandit timeout, bandit parse-error, detect-secrets timeout,
detect-secrets parse-error. Bunlarin hicbiri bir GUVENLIK BULGUSU degil; hepsi
"olcum yapilamadi" demek.
SONUC (duzeltilmezse): 'FAIL critical' etiketi hem gercek secret'i hem de calismamis
taramayi gosterir; ikisi ayirt edilemez -> kirmizi bilgi tasimaz.

KURAL: kontrol KOSTU ve BULDU -> FAIL. Kontrol KOSAMADI -> ERROR.
"""
import subprocess
import sys

import pytest

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _KASA_ROOT)

from tools.security_bench.checks import scan as scan_mod  # noqa: E402


@pytest.fixture()
def all_subprocess_timeout(monkeypatch):
    """Her dis alet cagrisini timeout'a dusur — 'alet cevap veremedi' senaryosu."""
    def _boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="fake", timeout=1)
    monkeypatch.setattr(scan_mod.subprocess, "run", _boom)
    return _boom


def test_timeout_never_reported_as_fail(all_subprocess_timeout):
    """Tum aletler timeout iken HICBIR kalem FAIL olmamali."""
    results = scan_mod.run()
    bad = [r for r in results if r["status"] == "FAIL"]
    assert not bad, (
        "kosamayan kontrol FAIL olarak raporlandi: "
        + "; ".join(f"{r['id']}={r['evidence'][:60]}" for r in bad))


def test_timeout_is_reported_as_error(all_subprocess_timeout):
    """Timeout'a dusen kalemler ERROR durumu tasimali (sessizce PASS de olmamali)."""
    results = scan_mod.run()
    timed_out = [r for r in results if "timed out" in (r.get("evidence") or "").lower()]
    assert timed_out, "timeout senaryosunda timeout kaniti tasiyan kalem uretilmedi"
    for r in timed_out:
        assert r["status"] == "ERROR", (
            f"{r['id']} timeout oldu ama durumu {r['status']} (beklenen ERROR)")


def test_timeout_never_reported_as_pass(all_subprocess_timeout):
    """NEGATIF KONTROL: 'olcemedim'i PASS'a cevirmek false-PASS olurdu — daha kotu."""
    results = scan_mod.run()
    for r in results:
        if "timed out" in (r.get("evidence") or "").lower():
            assert r["status"] != "PASS", f"{r['id']} timeout'u PASS sayildi (false-PASS)"


# Her aletin TEMIZ ciktisi farkli SEKILDEDIR; tek govde ucune birden uymaz:
#   bandit         -> {"results": [...]}   (LISTE)
#   pip-audit      -> {"dependencies": [...]}
#   detect-secrets -> {"results": {...}}   (SOZLUK: path -> bulgular)
# Tek sahte govde vermek, detect-secrets dalinda AttributeError uretir ve testi
# "alet bozuk cevap verdi" senaryosuna cevirir -> olcmek istedigimiz sey bu DEGIL.
_CLEAN_BY_TOOL = {
    "bandit": '{"results": []}',
    "pip_audit": '{"dependencies": []}',
    "detect_secrets": '{"results": {}}',
}


def _clean_proc_for(cmd):
    """Verilen komuta gore o aletin TEMIZ (bulgusuz) ciktisini taklit eder."""
    joined = " ".join(str(c) for c in (cmd or []))
    body = "{}"
    for tool, payload in _CLEAN_BY_TOOL.items():
        if tool in joined:
            body = payload
            break

    class _Proc:
        returncode = 0
        stderr = ""
        stdout = body

    return _Proc()


def test_clean_tool_output_does_not_become_error(monkeypatch):
    """NEGATIF KONTROL (hizli): alet DUZGUN cevap verdiginde ERROR'a kacmamali.
    ERROR yalniz 'cevap alinamadi' icindir; normal sonuclari da yutarsa yeni bir kor
    nokta acilir. Gercek taramayi kosmayiz (dakikalar surer) — temiz cikti taklit edilir."""
    monkeypatch.setattr(scan_mod.subprocess, "run",
                        lambda *a, **k: _clean_proc_for(a[0] if a else k.get("args")))
    results = scan_mod.run()
    assert results, "scan.run() hic sonuc uretmedi"
    errored = [r for r in results if r["status"] == "ERROR"]
    assert not errored, (
        "alet duzgun cevap verdigi halde ERROR uretildi: "
        + "; ".join(f"{r['id']}={r['evidence'][:60]}" for r in errored))


def test_unexpected_exception_is_not_silently_passed(monkeypatch):
    """NEGATIF KONTROL: beklenmedik istisna (bozuk govde) PASS sayilmamali.
    Bu, yukaridaki testin bosluga dusmesini onler — 'her seyi PASS yap' cozumu
    burada yakalanir."""
    class _Proc:
        returncode = 0
        stderr = ""
        stdout = '{"results": "bu bir metin, beklenen yapi degil"}'

    monkeypatch.setattr(scan_mod.subprocess, "run", lambda *a, **k: _Proc())
    results = scan_mod.run()
    scanners = [r for r in results if r["id"] in ("SCAN-BANDIT", "SCAN-SECRETS")]
    assert scanners, "tarayici kalemleri uretilmedi"
    for r in scanners:
        assert r["status"] != "PASS", (
            f"{r['id']} bozuk govdeyi PASS sayildi (false-PASS): {r['evidence'][:80]}")
