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
    error_count = sum(1 for r in results if r['status'] == 'ERROR')
    # ERROR ayri sayilir, FAIL'e EKLENMEZ. Ikisi farkli sorulara cevap verir:
    #   FAIL  = "olctuk, sorun bulduk"      -> duzeltilecek bir acik var
    #   ERROR = "olcemedik, arac cevap vermedi" -> duzeltilecek bir ALET var
    # Ayni sayaca konsalardi "kac acik var?" sorusu yanlis cevaplanirdi.

    unmeasured = [r for r in results
                  if r['status'] == 'ERROR' and r['severity'] in ('critical', 'high')]
    # KAPSAM KAPISI: kritik/yuksek onemde bir kontrol KOSMADIYSA sistem "temiz" ilan edilemez.
    # Sebep: "acik bulamadim" ile "acik yok" ayni sey degildir; "olcemedim" ise ikisinden de
    # farklidir. Bu ucu ayni yesile boyamak, sahte kirmizidan DAHA pahali bir yalan uretir --
    # kirmizi insani baktirir, yesil bakmayi biraktirir. Dusuk onemli alet arizalari kapiyi
    # tetiklemez, yoksa her kucuk aksaklik yayini kilitler ve kapi ise yaramaz hale gelir.

    verdict = (
        "## 🔴 YAYINA HAZIR DEĞİL (kritik açık)" if any(r['severity'] == 'critical' and r['status'] == 'FAIL' for r in results) else
        "## 🟠 RİSKLİ (yüksek açık)" if any(r['severity'] == 'high' and r['status'] == 'FAIL' for r in results) else
        "## 🟡 KÜÇÜK BULGULAR" if fail_count > 0 else
        "## ⚪ DOĞRULANMADI (kapsam eksik: %s)" % ", ".join(r['id'] for r in unmeasured) if unmeasured else
        "## 🟢 YAYIN-ADAYI"
    )
    # Sira onemli: GERCEK bulgular kapsam eksikliginden ONCE gelir. Bulunmus bir acik varken
    # "dogrulanmadi" demek acigi gizlemek olurdu; once bulunani soyle, sonra olculemeyeni.
    # Karar YALNIZCA status == 'FAIL' kalemlerine bakar; ERROR yayin engeli URETMEZ.
    # Sebep: kosamamis bir kontrol, "acik yok" kaniti olmadigi gibi "acik var" kaniti da
    # degildir. Onu kirmiziya boyamak, sahibi kirmiziya bakmamaya alistirir ve GERCEK acigin
    # gorulmesini zorlastirir. Yine de sessizce yutulmaz: asagida ayri bir bolumde listelenir
    # ve ozet tablosunda sayilir -- "olculemeyen" de bir bilgidir.

    markdown = [
        f"# KASA Güvenlik Benchmark — Kanıt Raporu",
        f"{meta['date']}, {meta['os']}, {meta['python']}",
        # v2 damga: rapor tek-basina denetlenebilir/tekrar-uretilebilir olsun (SPEC metodoloji disiplini)
        f"**Damga:** commit `{meta.get('commit', '?')}` · config-hash `{meta.get('config_hash', '?')}`"
        f" · WebView2 `{meta.get('webview2', 'n/a')}` · OS build `{meta.get('os_build', '?')}`"
        f" · katman **{meta.get('tier', 'base')}** · host `{meta.get('host', '?')}`",
        verdict,
        f"| Total | PASS | FAIL | ERROR | WARN | SKIP |",
        f"|-------|------|------|-------|------|------|",
        f"| {total} | {pass_count} | {fail_count} | {error_count} | {warn_count} | {skip_count} |"
        # ERROR sutunu FAIL'in yanina konur ki okuyan "kac acik, kac olculemeyen" ayrimini
        # tek bakista gorsun.
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
                'ERROR': '🔧',
                'WARN': '⚠️',
                'SKIP': '⏭️'
            }.get(result['status'], '❔')
            # ERROR icin anahtar/kirik-alet simgesi: sorun kodda degil OLCUM ALETINDE.
            # [] yerine .get(...) kullanilir: ileride tanimsiz bir durum gelirse rapor
            # KeyError ile comeden '❔' basar. Raporlayicinin cokmesi, raporlanan hatadan
            # daha pahalidir -- cunku o zaman HICBIR bulgu gorulemez.
            evidence = truncate_evidence(result['evidence'])
            markdown.append(f"| {result['id']} | {result['title']} | {status_emoji} {result['status']} | {result['severity']} | `{evidence}` |")

    error_list = [r for r in results if r['status'] == 'ERROR']
    if error_list:
        markdown.append("\n## Ölçülemeyenler (ERROR — bulgu değil)")
        markdown.append("_Bu kalemler bir açık bildirmiyor; aracın cevap veremediğini "
                        "bildiriyor. Yani bu alanlar **ölçülmemiştir** — ne temiz ne kirli._")
        for result in error_list:
            markdown.append(f"- {result['id']} ({result['severity']}): {result['evidence']}")
        # Ayri bolum, ERROR'un sessizce kaybolmasini onler. "Olcemedim" bilgisi, "temiz"
        # ile karistirilirsa kapsam yanilsamasi dogar: rapor 21 kontrol kostu gorunur ama
        # aslinda 20 kosmustur. Kapsami dogru bilmek, bulgulari bilmek kadar onemlidir.

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
        "counts": {"total": total, "PASS": pass_count, "FAIL": fail_count,
                   "ERROR": error_count, "WARN": warn_count, "SKIP": skip_count},
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
