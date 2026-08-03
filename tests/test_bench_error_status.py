# -*- coding: utf-8 -*-
"""
Olcum butunlugu kapisi — RAPORLAYICI tarafi (P0.1-A).

SEBEP: tools/security_bench 'kontrol kosamadi' durumunu 'kontrol bir sey buldu' ile ayni
kirmiziya boyuyor. 2026-08-01 kosusunda SCAN-SECRETS 'FAIL critical' basti; kaniti
"Scan timed out" idi -> tarama HIC kosmadi. Koasamayan kontrol BULGU DEGILDIR.
SONUC (duzeltilmezse): sahte kirmizi birikir, sahibi kirmiziya bakmayi birakir, gercek
acik goze carpmaz. Bu projede mühür = ölçüm; olcum aleti yalan soylerse muhur bostur.

Bu dosya YALNIZ report.render'in ERROR durumunu tasiyabilmesini kanitlar.
Uretimi (scan.py'nin ERROR uretmesi) kardes dosya test_bench_error_scan.py olcer.
"""
import sys

import pytest

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _KASA_ROOT)

from tools.security_bench.report import render  # noqa: E402

_META = {
    "date": "2026-08-01T00:00:00", "os": "Windows-11", "python": "3.14.5",
    "commit": "test", "config_hash": "test", "webview2": "n/a",
    "os_build": "test", "tier": "base", "host": "test",
}


def _result(status, severity="critical", cid="SCAN-SECRETS", evidence="Scan timed out."):
    return {
        "id": cid, "category": "scan", "title": "t",
        "status": status, "severity": severity,
        "evidence": evidence, "remediation": "r",
    }


def test_render_accepts_error_status_without_crashing():
    """ERROR durumu render'i patlatmamali (bugun emoji sozluginde KeyError)."""
    md, js = render([_result("ERROR")], _META)
    assert isinstance(md, str) and isinstance(js, str)
    assert "SCAN-SECRETS" in md


def test_error_is_counted_separately_from_fail():
    """ERROR, FAIL sayacina KARISMAMALI — yoksa 'kac acik var' sorusu yanlis cevaplanir."""
    import json
    _, js = render([_result("ERROR"), _result("PASS", cid="AUTHZ-BIND")], _META)
    counts = json.loads(js)["counts"]
    assert counts.get("ERROR") == 1, f"ERROR ayri sayilmali, counts={counts}"
    assert counts.get("FAIL") == 0, f"ERROR, FAIL olarak sayilmis: {counts}"


# Urunun verdict sozlesmesi. Testler bu SABITLERE bakar, serbest metne degil.
# SEBEP: 'assert "X" not in verdict' bicimindeki negatif iddia, X biraz degisirse
# KENDILIGINDEN gecer -> sahte yesil. Beklenen degeri acikca listeleyip "hangisi
# uretildi" diye sormak bu bosluga dusmez.
BLOCKING_VERDICT = "YAYINA HAZIR DEĞİL"
CLEAN_VERDICT = "YAYIN-ADAYI"
UNVERIFIED_VERDICT = "DOĞRULANMADI"


def test_critical_error_does_not_trigger_release_blocking_verdict():
    """SEBEP->SONUC: 'olcemedim' ile 'kritik acik buldum' AYNI SEY DEGILDIR.

    Kosamayan bir kontrol yayin-ENGELI uretmemeli: engel, BULUNMUS bir acigin sonucudur;
    olculmemis alan icin engel demek, olmayan bir bulguyu iddia etmek olur (kurt masali).
    Ama yesil de olamaz -- olcum bosluguyla temizlik ayni sey degildir (bkz.
    test_bench_coverage_verdict.py). Dogru cevap ucuncu durum: DOGRULANMADI.
    Bu test 'kirmizi degil'i, kardes dosya 'yesil degil'i korur; ikisi birlikte tek dogru
    hucreyi kapatir."""
    import json
    _, js = render([_result("ERROR", severity="critical"), _result("PASS", cid="AUTHZ-BIND")], _META)
    verdict = json.loads(js)["verdict"]
    assert BLOCKING_VERDICT not in verdict, (
        f"kosamayan kontrol yayin-engeli uretti (sahte kirmizi); verdict={verdict!r}")
    # Bosluga dusmeyi onleyen ikinci sart: verdict TANINAN bir deger olmali.
    # Boylece dize degisip negatif iddia bosa dustugunde test SESSIZCE gecmez.
    assert UNVERIFIED_VERDICT in verdict, (
        f"verdict taninmiyor — urun metni degismis olabilir, test bosa dusuyor: {verdict!r}")


def test_real_critical_fail_still_blocks_release():
    """NEGATIF KONTROL: gercek kritik FAIL hala yayin-engeli uretmeli.
    (ERROR eklemek, gercek bulgulari yumusatmamali — false-PASS kapisi.)"""
    import json
    _, js = render([_result("FAIL", severity="critical")], _META)
    verdict = json.loads(js)["verdict"]
    assert BLOCKING_VERDICT in verdict, (
        f"gercek kritik FAIL yayin-engeli URETMEDI; verdict={verdict!r}")


def test_error_is_visible_in_markdown_not_silently_dropped():
    """ERROR gorunur kalmali — sessizce yutulursa 'olcemedim' bilgisi kaybolur."""
    md, _ = render([_result("ERROR")], _META)
    assert "ERROR" in md, "ERROR durumu markdown raporda gorunmuyor"
