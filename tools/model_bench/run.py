# kasa/tools/model_bench/run.py

"""
Tezgah surucusu: bir veya daha fazla model adayini olcer, damga uretir.

Kullanim:
    py -3.14 -m tools.model_bench --model hermes3:8b
    py -3.14 -m tools.model_bench --model hermes3:8b,qwen2.5:7b,qwen2.5:3b

Turkce not: modeller SIRAYLA olculur (paralel DEGIL) — 12.2 GB VRAM'de es-zamanli yukleme
tahliye/yeniden-yukleme cirpinmasina ve cokmeye yol acar (bu makinede yasandi).
Her modelden sonra servis modeli bosaltsin diye kisa bekleme konur.
"""

from __future__ import annotations

import argparse
import datetime
import os
import platform
import socket
import subprocess
import sys
import time

if "d:/kasa" not in sys.path:
    sys.path.insert(0, "d:/kasa")

from tools.model_bench import probes
from tools.model_bench.report import render

DOCS_DIR = "d:/kasa/docs"
COOLDOWN_S = 10  # modeller arasi soguma (GPU nefes alsin)


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "-C", "d:/kasa", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _installed() -> set[str]:
    """Kurulu model adlari — olcumden ONCE dogrulanir (yoksa bos rapor uretmeyelim)."""
    ok, models = probes.harness.list_installed_models()
    return {m["name"] for m in models} if ok else set()


def _slug(model: str) -> str:
    """hermes3:8b -> hermes3-8b (dosya adi guvenli)."""
    return model.replace(":", "-").replace("/", "-")


def bench_one(model: str) -> dict:
    """Tek model: tum problar sirayla, sonra damga yaz. Doner: ozet sozluk."""
    meta = {
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "python": platform.python_version(),
        "commit": _git_commit(),
    }
    results: list[dict] = []
    for probe in probes.ALL_PROBES:
        name = probe.__name__
        print(f"  [{model}] {name} ...", flush=True)
        started = time.time()
        try:
            results.extend(probe(model))
        except Exception as e:  # prob cokerse tezgah durmaz, kanit olarak yazilir
            results.append({"id": f"MB-{name}-CRASH", "category": "toolcall",
                            "title": f"{name} çöktü", "status": "FAIL", "severity": "critical",
                            "evidence": f"{type(e).__name__}: {e}", "remediation": "prob hatası",
                            "score": 0.0})
        print(f"      -> {time.time() - started:.1f}s", flush=True)

    md, js = render(model, results, meta)
    os.makedirs(DOCS_DIR, exist_ok=True)
    slug = _slug(model)
    with open(os.path.join(DOCS_DIR, f"MODEL_BENCH_{slug}.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(DOCS_DIR, f"model_bench_{slug}.json"), "w", encoding="utf-8") as f:
        f.write(js)

    import json as _json
    summary = _json.loads(js)
    return {"model": model, "verdict": summary["verdict"],
            "score": summary["overall_score"], "counts": summary["counts"]}


def main() -> int:
    ap = argparse.ArgumentParser(description="KASA model ölçüm tezgahı (F0)")
    ap.add_argument("--model", required=True, help="virgülle ayrılmış model adları")
    args = ap.parse_args()

    wanted = [m.strip() for m in args.model.split(",") if m.strip()]
    installed = _installed()
    if not installed:
        print("HATA: yerel model servisi kapalı (127.0.0.1:11434).")
        return 2
    missing = [m for m in wanted if m not in installed]
    if missing:
        print(f"HATA: kurulu değil: {missing}")
        return 2

    summaries = []
    for i, model in enumerate(wanted):
        print(f"\n=== {model} ({i + 1}/{len(wanted)}) ===", flush=True)
        summaries.append(bench_one(model))
        if i + 1 < len(wanted):
            time.sleep(COOLDOWN_S)

    print("\n=== ÖZET ===")
    for s in summaries:
        c = s["counts"]
        print(f"{s['model']:<28} skor={s['score']:>5}  {s['verdict']:<24} "
              f"PASS={c['PASS']} FAIL={c['FAIL']} WARN={c['WARN']} SKIP={c['SKIP']}")
    print(f"\nDamgalar: {DOCS_DIR}/MODEL_BENCH_*.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
