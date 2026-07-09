import json
from typing import List, Dict, Tuple

def render(results: List[Dict], meta: Dict) -> Tuple[str, str]:
    def truncate_evidence(evidence: str, max_length: int = 160) -> str:
        if len(evidence) > max_length:
            return evidence[:max_length].rsplit(' ', 1)[0] + '...'
        return evidence

    total = len(results)
    pass_count = sum(1 for r in results if r['status'] == 'PASS')
    fail_count = sum(1 for r in results if r['status'] == 'FAIL')
    warn_count = sum(1 for r in results if r['status'] == 'WARN')
    skip_count = sum(1 for r in results if r['status'] == 'SKIP')

    verdict = (
        "## 🔴 YAYINA HAZIR DEĞİL (kritik açık)" if any(r['severity'] == 'critical' and r['status'] == 'FAIL' for r in results) else
        "## 🟠 RİSKLİ (yüksek açık)" if any(r['severity'] == 'high' and r['status'] == 'FAIL' for r in results) else
        "## 🟡 KÜÇÜK BULGULAR" if fail_count > 0 else
        "## 🟢 YAYIN-ADAYI"
    )

    markdown = [
        f"# KASA Güvenlik Benchmark — Kanıt Raporu",
        f"{meta['date']}, {meta['os']}, {meta['python']}",
        # v2 damga: rapor tek-basina denetlenebilir/tekrar-uretilebilir olsun (SPEC metodoloji disiplini)
        f"**Damga:** commit `{meta.get('commit', '?')}` · config-hash `{meta.get('config_hash', '?')}`"
        f" · WebView2 `{meta.get('webview2', 'n/a')}` · OS build `{meta.get('os_build', '?')}`"
        f" · katman **{meta.get('tier', 'base')}** · host `{meta.get('host', '?')}`",
        verdict,
        f"| Total | PASS | FAIL | WARN | SKIP |",
        f"|-------|------|------|------|------|",
        f"| {total} | {pass_count} | {fail_count} | {warn_count} | {skip_count} |"
    ]

    tables = {}
    for category in ['authz', 'crypto', 'audit', 'scan', 'fuzz']:
        tables[category] = [r for r in results if r['category'] == category]
        markdown.append(f"\n## {category.capitalize()}")
        markdown.append("| ID | Başlık | Durum | Önem | Kanıt |")
        markdown.append("|----|--------|-------|-------|-------|")
        for result in tables[category]:
            status_emoji = {
                'PASS': '✅',
                'FAIL': '❌',
                'WARN': '⚠️',
                'SKIP': '⏭️'
            }[result['status']]
            evidence = truncate_evidence(result['evidence'])
            markdown.append(f"| {result['id']} | {result['title']} | {status_emoji} {result['status']} | {result['severity']} | `{evidence}` |")

    remediation_list = [r for r in results if r['status'] != 'PASS']
    markdown.append("\n## Düzeltme Önerileri")
    for result in remediation_list:
        markdown.append(f"- {result['id']}: {result.get('remediation', '')}")

    markdown.append("\n## Bilinen Sınırlar (dürüst)")
    markdown.append("- fingerprint B1/B3/B4 still open;")
    markdown.append("- non-Windows DPAPI no-op;")
    markdown.append("- this benchmark does not cover network MITM or physical access.")

    json_data = {
        "meta": meta,
        "verdict": ' '.join(verdict.split(' ')[2:]),  # "## <emoji> TEXT" -> TEXT
        "counts": {"total": total, "PASS": pass_count, "FAIL": fail_count, "WARN": warn_count, "SKIP": skip_count},
        "results": results
    }

    markdown_text = '\n'.join(markdown)
    json_text = json.dumps(json_data, ensure_ascii=False, indent=2)

    return markdown_text, json_text


# ===== NEDEN -> SONUC / CAUSE -> EFFECT (yerel model, sifir-token) =====
# Purpose: Generates a security report in Markdown and JSON formats.
# Why (cause -> effect): The function processes test results and metadata to create a detailed report that highlights the status of various security checks. This helps stakeholders understand the security posture of their systems.
# Amac: Güvenlik raporu oluşturur.
# Neden -> Sonuc: Bu işlev, test sonuçlarını ve meta verileri işleyerek çeşitli güvenlik denetimlerinin durumunu ayrıntılı bir şekilde gösteren bir rapor oluşturur. Bu, yetkililere sistemlerinin güvenlik düzeyini anlamalarına yardımcı olur.
