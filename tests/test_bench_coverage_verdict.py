# -*- coding: utf-8 -*-
"""
Kapsam kapisi: olculmeyen alan, YESIL karar uretemez.

SEBEP: 2026-08-02'de timeout'u FAIL'den ayirip ERROR yaptik. Siniflandirma dogruydu ama
karar mantigi yarim kaldi: kritik onemdeki SCAN-SECRETS hic kosmadigi halde verdict
"YAYIN-ADAYI" cikti. Yani bir yalani (sahte kirmizi) duzeltirken ikincisinin (sahte yesil)
kapisini araladik.
SONUC (duzeltilmezse): kirmizi insani BAKTIRIR, yesil bakmayi BIRAKTIRIR. Olculmemis bir
alani "temiz" gibi gosteren yesil, sahte kirmizidan daha pahalidir -- cunku kimse doniip
kontrol etmez. Kapsam eksikligi, bulgu yoklugu ile ayni sey DEGILDIR:
  "acik bulamadim"  != "acik yok"
  ve  "olcemedim"   != "acik bulamadim"
KARAR: kritik/yuksek onemde bir kontrol kosmadiysa verdict ucuncu bir duruma duser --
ne yesil ne kirmizi: DOGRULANMADI (kapsam eksik).
"""
import json
import sys

sys.path.insert(0, "d:/kasa")

from tools.security_bench.report import render  # noqa: E402

_META = {
    "date": "2026-08-02T00:00:00", "os": "Windows-11", "python": "3.14.5",
    "commit": "test", "config_hash": "test", "webview2": "n/a",
    "os_build": "test", "tier": "base", "host": "test",
}

BLOCKING_VERDICT = "YAYINA HAZIR DEĞİL"
CLEAN_VERDICT = "YAYIN-ADAYI"
UNVERIFIED_VERDICT = "DOĞRULANMADI"


def _r(status, severity="critical", cid="SCAN-SECRETS", evidence="Scan timed out."):
    return {"id": cid, "category": "scan", "title": "t", "status": status,
            "severity": severity, "evidence": evidence, "remediation": "r"}


def _verdict(results):
    return json.loads(render(results, _META)[1])["verdict"]


def test_critical_error_blocks_clean_verdict():
    """Kritik bir kontrol kosmadiysa 'yayin adayi' denemez."""
    v = _verdict([_r("ERROR", "critical"), _r("PASS", "critical", cid="AUTHZ-BIND")])
    assert CLEAN_VERDICT not in v, f"olculmemis kritik alan YESIL karar uretti: {v!r}"
    assert UNVERIFIED_VERDICT in v, f"beklenen 'DOGRULANMADI' durumu uretilmedi: {v!r}"


def test_high_error_also_blocks_clean_verdict():
    """Yuksek onemde kosmayan kontrol de yesili engellemeli."""
    v = _verdict([_r("ERROR", "high", cid="SCAN-BANDIT"), _r("PASS", "critical", cid="AUTHZ-BIND")])
    assert CLEAN_VERDICT not in v, f"olculmemis yuksek-onem alan YESIL karar uretti: {v!r}"


def test_low_severity_error_does_not_block():
    """NEGATIF KONTROL: dusuk onemde kosmayan kontrol yesili engellememeli.
    Aksi halde her kucuk alet arizasi yayini kilitler ve kapi ise yaramaz hale gelir."""
    v = _verdict([_r("ERROR", "info", cid="CRYPTO-DPAPI"), _r("PASS", "critical", cid="AUTHZ-BIND")])
    assert CLEAN_VERDICT in v, f"dusuk-onem alet arizasi yesili gereksiz yere engelledi: {v!r}"


def test_real_critical_fail_still_outranks_unverified():
    """NEGATIF KONTROL: gercek kritik bulgu, kapsam eksikliginden ONCE gelir.
    Bulunmus bir acik varken 'dogrulanmadi' demek, acigi gizlemek olurdu."""
    v = _verdict([_r("FAIL", "critical"), _r("ERROR", "critical", cid="SCAN-BANDIT")])
    assert BLOCKING_VERDICT in v, f"gercek kritik FAIL yayin-engelini kaybetti: {v!r}"


def test_all_clean_still_reaches_clean_verdict():
    """NEGATIF KONTROL: hicbir ERROR yokken yesil hala ulasilabilir olmali.
    Kapi, yesili IMKANSIZ hale getirirse anlamsizlasir."""
    v = _verdict([_r("PASS", "critical", cid="AUTHZ-BIND"), _r("WARN", "medium", cid="SCAN-BAK-HYGIENE")])
    assert CLEAN_VERDICT in v, f"tamamen temiz kosuda yesil uretilmedi: {v!r}"
