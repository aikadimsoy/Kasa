# -*- coding: utf-8 -*-
"""KASA loop -- N tur otonom soak-run + final rapor. Sadece orkestrasyon/raporlama;
fix kodu uretmez (mevcut loop_runner + yerel modelleri kullanir). Claude bu dongude YOK --
baslatilip arka planda tek basina kosar, sonunda RUN40_REPORT.md yazar."""
import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from loop_runner import LoopRunner

BOARD = os.path.join(HERE, "board.json")
LOGS = os.path.join(HERE, "logs")
os.makedirs(LOGS, exist_ok=True)
N = int(os.environ.get("KASA_LOOP_CYCLES", "40"))

t0 = time.time()
cycles = []
for i in range(1, N + 1):
    runner = LoopRunner(BOARD)
    results = runner.run_all()
    cycles.append({"cycle": i, "ts": datetime.now(timezone.utc).isoformat(), "results": results})
    with open(os.path.join(LOGS, "run40_summary.json"), "w", encoding="utf-8") as f:
        json.dump(cycles, f, ensure_ascii=False, indent=2)

dur = round(time.time() - t0, 1)

all_ids = sorted({r["id"] for c in cycles for r in c["results"]})
edits_by_job = {}
final_status = {}
for c in cycles:
    for r in c["results"]:
        if r.get("edited"):
            edits_by_job.setdefault(r["id"], []).append(c["cycle"])
        final_status[r["id"]] = r["outcome"]

lines = []
lines.append("# KASA 40x Otonom Guvenlik Dongusu -- Rapor\n\n")
lines.append(f"- Tur sayisi: {N}\n- Toplam sure: {dur}s\n- Bitis (UTC): {datetime.now(timezone.utc).isoformat()}\n\n")
lines.append("## Is basina sonuc\n\n")
for jid in all_ids:
    edits = edits_by_job.get(jid, [])
    lines.append(
        f"- **{jid}**: son durum = `{final_status.get(jid)}`, "
        f"gercek duzenleme yapilan tur sayisi = {len(edits)}"
        + (f" (turlar: {edits})" if edits else "") + "\n"
    )

lines.append("\n## Bu kosuda olusan .bak yedekleri (degisen dosyalar)\n\n")
bak_found = False
for root, _, files in os.walk(REPO):
    if (os.sep + ".git") in root or "node_modules" in root:
        continue
    for fn in files:
        if ".bak_loop_" in fn:
            bak_found = True
            lines.append(f"- {os.path.relpath(os.path.join(root, fn), REPO)}\n")
if not bak_found:
    lines.append("- (bu kosuda yeni .bak yedegi olusmadi -- ilk turda her sey zaten yesildi)\n")

lines.append(
    "\n## Ham veri\n"
    "- Tur-tur detay: `_orch/loop/logs/run40_summary.json`\n"
    "- Olay akisi: `_orch/loop/logs/loop_events.jsonl`\n"
    "- KPI: `_orch/loop/logs/loop_kpi.json`\n"
    "- Journal: `_orch/loop/logs/loop_journal.md`\n"
)

report_path = os.path.join(LOGS, "RUN40_REPORT.md")
with open(report_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("RUN40_DONE:", report_path, flush=True)
