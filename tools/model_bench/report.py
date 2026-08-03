# kasa/tools/model_bench/report.py

"""
Olcum raporu — markdown damgasi + JSON.

Turkce not: rapor tek basina denetlenebilir olsun diye her kosuya commit + host + tarih
damgasi basilir (security_bench/report.py ile ayni disiplin). Karar cumlesi IDDIA degil,
sayilardan turetilir.
"""

from __future__ import annotations

import json

CATEGORY_TITLES = {
    "toolcall": "Araç çağrısı (ajan yolu)",
    "loop": "Döngü davranışı",
    "refusal": "Reddetme (sahibin kendi verisi)",
    "json": "Katı JSON (damıtma yolu)",
    "injection": "Enjeksiyon direnci",
    "lang": "İki dillilik",
}

_EMOJI = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "SKIP": "⏭️"}


def verdict_of(results: list[dict]) -> tuple[str, str]:
    """Karar: kritik FAIL varsa rol icin UYGUN DEGIL. Sayidan turetilir, elle yazilmaz."""
    crit = [r for r in results if r["status"] == "FAIL" and r["severity"] == "critical"]
    high = [r for r in results if r["status"] == "FAIL" and r["severity"] == "high"]
    if crit:
        return "ROL İÇİN UYGUN DEĞİL", f"🔴 kritik başarısızlık: {', '.join(r['id'] for r in crit)}"
    if high:
        return "KOŞULLU UYGUN", f"🟠 yüksek önemde açık: {', '.join(r['id'] for r in high)}"
    if any(r["status"] == "WARN" for r in results):
        return "UYGUN (küçük bulgular)", "🟡 küçük bulgular var"
    return "UYGUN", "🟢 tüm kritik ölçütler geçti"


def render(model: str, results: list[dict], meta: dict) -> tuple[str, str]:
    total = len(results)
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL", "WARN", "SKIP")}
    verdict, why = verdict_of(results)

    scored = [r["score"] for r in results if r.get("score") is not None]
    overall = round(sum(scored) / len(scored), 1) if scored else 0.0

    md = [
        f"# KASA Model Ölçümü — `{model}`",
        f"{meta['date']} · {meta['host']} · commit `{meta['commit']}` · Python {meta['python']}",
        "",
        f"## {why}",
        f"**Karar: {verdict}** · genel skor **{overall}/100**",
        "",
        "| Toplam | PASS | FAIL | WARN | SKIP |",
        "|--------|------|------|------|------|",
        f"| {total} | {counts['PASS']} | {counts['FAIL']} | {counts['WARN']} | {counts['SKIP']} |",
    ]

    for cat, title in CATEGORY_TITLES.items():
        rows = [r for r in results if r["category"] == cat]
        if not rows:
            continue
        md += ["", f"## {title}", "| ID | Ölçüt | Durum | Önem | Skor | Kanıt |",
               "|----|-------|-------|------|------|-------|"]
        for r in rows:
            score = "—" if r.get("score") is None else f"{r['score']}"
            ev = r["evidence"].replace("|", "\\|").replace("\n", " ")[:150]
            md.append(f"| {r['id']} | {r['title']} | {_EMOJI[r['status']]} {r['status']} "
                      f"| {r['severity']} | {score} | `{ev}` |")

    problems = [r for r in results if r["status"] in ("FAIL", "WARN") and r.get("remediation")]
    if problems:
        md += ["", "## Ne yapılmalı"]
        md += [f"- **{r['id']}**: {r['remediation']}" for r in problems]

    md += [
        "", "## Dürüst sınırlar",
        "- Enjeksiyon direnci **yumuşak** bir ölçüdür; gerçek güvenlik sınırı `src/agent/gate.py`'dir (KURALLAR §4).",
        "- A5/A6 notlaması `heuristic` işaretlidir — kural tabanlı, LLM-notlayıcı değil; kanıt sütununda yöntem yazılıdır.",
        "- Bu tezgah **ölçer, düzeltmez** (docs/adr/0002 ile aynı ilke).",
        "- Tek koşu; modeller stokastiktir. Sınırdaki sonuçlar tekrar koşulmalıdır.",
    ]

    js = json.dumps({"model": model, "meta": meta, "verdict": verdict,
                     "overall_score": overall, "counts": counts, "results": results},
                    ensure_ascii=False, indent=2)
    return "\n".join(md), js
