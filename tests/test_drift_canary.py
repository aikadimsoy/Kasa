# -*- coding: utf-8 -*-
"""L4 drift-canary KALICI regresyon (Controller): deterministik delta-tespiti gercekten isirir."""
import sys
import os
import json
import tempfile

sys.path.insert(0, "d:/kasa")
from tools import drift_canary as dc


def test_snapshot_has_tracked_keys():
    s = dc.snapshot()
    assert set(s.keys()) == {"webview2", "config_hash", "os_build"}


def test_no_drift_when_baseline_matches():
    tmp = os.path.join(tempfile.mkdtemp(), "baseline.json")
    dc.write_baseline(tmp)                 # simdiki durumu baseline yap
    res = dc.compare(tmp)
    assert res["status"] == "ok" and res["diff"] == {}


def test_drift_detected_when_baseline_differs():
    tmp = os.path.join(tempfile.mkdtemp(), "baseline.json")
    cur = dc.snapshot()
    # WebView2 sessiz-guncelleme simulasyonu: baseline'a SAHTE eski surum yaz
    fake = dict(cur); fake["webview2"] = "0.0.0.0-ESKI"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(fake, f)
    res = dc.compare(tmp)
    assert res["status"] == "drift", res
    assert "webview2" in res["diff"]
    assert res["diff"]["webview2"]["baseline"] == "0.0.0.0-ESKI"
    assert res["diff"]["webview2"]["current"] == cur["webview2"]


def test_baseline_missing_reported():
    tmp = os.path.join(tempfile.mkdtemp(), "yok.json")
    res = dc.compare(tmp)
    assert res["status"] == "baseline_missing"
