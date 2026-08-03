# -*- coding: utf-8 -*-
"""
Guvenlik benchmark'i icin KALICI regresyon testleri (Controller).
Amac: yerel modelin daha once uretttigi iki hatayi bir daha SESSIZCE geri getirememesi:
  (1) fuzz FUZZ-EXECUTE/NOAUTH ters PASS/FAIL mantigi (cokme -> yanlislikla PASS),
  (2) evidence sayiminda off-by-one ("N > gonderilen payload").
"tek sefer kanitla" degil "surekli kanitla".
"""
import re
import sys
from unittest.mock import patch

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _KASA_ROOT)
from tools.security_bench.checks import fuzz


class _Resp500:
    status_code = 500


def _run_fuzz_all_5xx():
    with patch.object(fuzz, "TestClient") as TC:
        client = TC.return_value.__enter__.return_value
        client.post.return_value = _Resp500()
        results = fuzz.run()
    return {r["id"]: r for r in results}


def test_fuzz_negative_control_forced_5xx_is_FAIL():
    """Sunucu her istekte 5xx dondurse fuzz checkleri FAIL basmali (rubber-stamp degil)."""
    by_id = _run_fuzz_all_5xx()
    assert by_id["FUZZ-EXECUTE"]["status"] == "FAIL"
    assert by_id["FUZZ-NOAUTH"]["status"] == "FAIL"


def test_fuzz_evidence_count_not_off_by_one():
    """FUZZ-EXECUTE evidence'indaki '5xx' sayisi gonderilen payload sayisini ASMAMALI."""
    by_id = _run_fuzz_all_5xx()
    ev = by_id["FUZZ-EXECUTE"]["evidence"]
    m = re.search(r"(\d+) malformed payloads sent, (\d+) caused 5xx", ev)
    assert m, "evidence formati beklenenden farkli: " + ev
    sent, caused = int(m.group(1)), int(m.group(2))
    assert caused <= sent, f"off-by-one: {caused} caused > {sent} sent"
