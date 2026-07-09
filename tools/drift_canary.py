# -*- coding: utf-8 -*-
"""
L4 DRIFT CANARY — deterministik delta-monitor (plan §2 ilke 11: AI degil, DETERMINISTIK).

Neden: benchmark anlik bir fotograf. WebView2 sessizce guncellenince ya da config degisince
bugunku PASS yarin YALAN olabilir. Canary WebView2 surumu + config-hash + OS build'i baseline'la
karsilastirir; DEGISIRSE uyarir ve (--rerun ile) benchmark'i yeniden kosar. Bastirma/karar
MODELE degil deterministik karsilastirmaya baglidir; baseline guncellemesi insan-incelemesi ister.

Kullanim:
  python tools/drift_canary.py --update     # baseline'i simdiki duruma ayarla (inceleme sonrasi)
  python tools/drift_canary.py              # karsilastir; drift varsa exit!=0
  python tools/drift_canary.py --rerun      # drift'te benchmark'i yeniden kos
"""
import sys
import os
import json
import platform
import argparse
import subprocess

sys.path.insert(0, "d:/kasa")
from tools.security_bench.run import _webview2_version, _config_hash

DEFAULT_BASELINE = "d:/kasa/docs/drift_baseline.json"


def snapshot() -> dict:
    """Izlenen deterministik parmak izleri (sec-ch-ua platform ~ os_build ile temsil edilir)."""
    return {
        "webview2": _webview2_version(),
        "config_hash": _config_hash(),
        "os_build": platform.version(),
    }


def compare(baseline_path: str = DEFAULT_BASELINE) -> dict:
    """(status, diff, current) dondurur. status: 'baseline_missing' | 'ok' | 'drift'."""
    cur = snapshot()
    try:
        with open(baseline_path, encoding="utf-8") as f:
            base = json.load(f)
    except FileNotFoundError:
        return {"status": "baseline_missing", "diff": {}, "current": cur}
    diff = {k: {"baseline": base.get(k), "current": cur[k]} for k in cur if base.get(k) != cur[k]}
    return {"status": "drift" if diff else "ok", "diff": diff, "current": cur, "baseline": base}


def write_baseline(baseline_path: str = DEFAULT_BASELINE) -> dict:
    cur = snapshot()
    os.makedirs(os.path.dirname(baseline_path), exist_ok=True)
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(cur, f, indent=2)
    return cur


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    ap.add_argument("--update", action="store_true", help="baseline'i simdiki duruma ayarla")
    ap.add_argument("--rerun", action="store_true", help="drift'te benchmark'i yeniden kos")
    args = ap.parse_args()

    if args.update:
        cur = write_baseline(args.baseline)
        print("[drift] baseline guncellendi:", json.dumps(cur))
        return 0

    res = compare(args.baseline)
    if res["status"] == "baseline_missing":
        cur = write_baseline(args.baseline)
        print("[drift] baseline YOKTU -> kuruldu:", json.dumps(cur))
        return 0
    if res["status"] == "ok":
        print("[drift] degisiklik YOK:", json.dumps(res["current"]))
        return 0

    # drift
    print("[drift] !!! DRIFT TESPIT EDILDI:", json.dumps(res["diff"], ensure_ascii=False))
    if args.rerun:
        print("[drift] benchmark yeniden kosuluyor (drift-tetikli)...")
        subprocess.run([sys.executable, "-m", "tools.security_bench"], cwd="d:/kasa")
    print("[drift] NOT: degisim INCELENDIKTEN sonra --update ile baseline'i guncelle (otomatik degil).")
    return 3  # drift -> non-zero (cron/CI yakalasin)


if __name__ == "__main__":
    raise SystemExit(main())
