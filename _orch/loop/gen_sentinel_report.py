# -*- coding: utf-8 -*-
"""
gen_sentinel_report.py — SIFIR-TOKEN orkestrasyon (yalnizca boru hatti; RAPOR-ONLY).
deepseek taslak -> qwen inceleme -> <ev-dizini>/Desktop/KASA_sentinel_karsilastirma_2026-07-09.md
Prose YEREL modellerden gelir; bu dosya icerik uretmez, SPEC'i tasir ve ciktiyi yazar.
Kanit: Controller/opus WebFetch ciktilari (MarketNow/Sentinel) — SPEC'e gomulu, modeller disina cikamaz.
Calistirma:
  python gen_sentinel_report.py                (tam tur: deepseek + qwen)
  python gen_sentinel_report.py --review-only  (mevcut raporu qwen'e yeniden incelet)
"""
import os, sys, re, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_pipe import call_model, DRAFTER, REVIEWER, ollama_up

# Turkce not: cikti sabit bir kullanici Masaustune yaziliyordu (hesap adi sizinti);
# artik ev dizininden turetilir, KASA_REPORT_OUT ile degistirilebilir.
OUT = os.environ.get("KASA_REPORT_OUT") or os.path.join(
    os.path.expanduser("~"), "Desktop", "KASA_sentinel_karsilastirma_2026-07-09.md")

# ---------------------------------------------------------------------------
# SPEC — faktuel iskelet (sef tarafindan verilen KANIT; modeller bunun disina cikamaz)
# ---------------------------------------------------------------------------
SPEC = """Baslik: "MarketNow 'Sentinel' Sertifikalari vs KASA Guvenlik Yapisi — Karsilastirma Raporu (2026-07-09)"

Belge TURKCE yazilacak; teknik terimler (HMAC, SHA-256, DPAPI, AES-GCM, gVisor, MCP, semgrep, OSV vb.)
Ingilizce kalabilir. Asagidaki 6 bolum, bu sirayla, duzgun markdown hiyerarsisiyle (#, ##) yer almali.
Rapor bir DEGERLENDIRME notudur: owner (kullanici) okuyup karar verecek. Kanit disina CIKMA,
yeni olgu/sayi/API UYDURMA.

=== KANIT: MarketNow / Sentinel (WebFetch ile toplanan gercek veri) ===
- MarketNow: public MCP skill marketplace. "Sentinel" = skill-basina denetim sertifikasi sistemi.
- Sertifika dosyasi (sentinel_certificates/mn-acm-001.json ornegi) alanlari: certificate_id, skill_id,
  skill_name, issued_at, expires_at (7 gun gecerli), auditor ("Sentinel L1.5+L1.6+L2"),
  overall_score/max_score (ornek 9/10), risk_level, risk_breakdown{l15_l16, l2, final},
  layers_run{l15, l16, l2 bool}, layer_details{semgrep/secret/osv bulgu sayilari},
  signature (SHA-256 hex), signature_algorithm, verification_url.
- KRITIK TEKNIK NOT: signature alani DUZ SHA-256 = tamper-EVIDENCE saglar ama asimetrik imza DEGILDIR;
  anahtar yok, iceigi degistiren biri hash'i YENIDEN HESAPLAYABILIR. Yani sertifika kendi basina
  sahtecilige karsi koruma saglamaz.
- _summary.json (agrega): generated_at, total_certified (10978 skill), total_failed,
  by_risk{low/medium/high/critical}, by_score{0..10 histogram}, with_l2, l2_coverage_pct.
- marketnow.site/security sayfasi iddialari: "Sentinel L1.5 = her skill'e 6-nokta MCP denetimi,
  metodoloji public"; "her mandate transaction bir git commit (_data/mandates/), tam auditable";
  gVisor sandbox (L2.5). WebFetch degerlendirmesi: sayfanin teknik derinligi ZAYIF, marketing-agirlikli;
  gVisor gibi iddialar dogrulanamadi.

=== KANIT: KASA'nin mevcut yapisi (kiyas ekseni) ===
- Benchmark v2 raporu: 21 kontrol, her biri PASS/FAIL/WARN/SKIP + severity; meta STAMP
  (commit / config-hash / webview2 / os-build / tier); verdict kurali: herhangi bir KRITIK FAIL varsa
  "YAYINA HAZIR DEGIL". EKSIK: results'in kendisinin hash'i/imzasi YOK — rapor tamper-evident DEGIL.
- AuditChain: hash-zincirli tamper-evident audit log (her kayit onceki kaydin hash'ini icerir).
- L2 at-rest: DPAPI ile korunan _db_key + app-layer AES-GCM (profile.value / events.content /
  audit.details kolonlari sifreli).
- L4 drift-canary: WebView2 veya config degistiginde benchmark'in yeniden kosulmasini tetikler
  (gecerlilik zamana degil ORTAM DEGISIMINE bagli, olay-tetiklemeli).
- Tehdit modeli: KASA private local vault; kod owner'in KENDI kodu (N=1 urun); dusman = ayni-makine
  local malware ve bulut-sync sizintisi. MarketNow ise public marketplace: 10978 adet UNTRUSTED
  ucuncu-parti skill'i yabancilara karsi denetleyip guven satmak zorunda.

=== BOLUM PLANI (6 bolum, bu sirayla) ===

1. NE BUNLAR (kisa):
MarketNow = public MCP skill marketplace; Sentinel = skill-basina JSON denetim sertifikasi
(L1.5 statik 6-nokta denetim + L1.6 + L2 katmanlari; semgrep/secret/OSV bulgu sayimlari),
7 gunluk expires_at, 0-10 skor, public verification_url, agrega _summary.json (10978 sertifika).
Site guvenlik anlatisi marketing-agirlikli; gVisor sandbox iddiasi dogrulanamadi.

2. YAPISAL KIYAS TABLOSU (markdown tablo; kolonlar: "Sentinel alani/deseni" | "KASA karsiligi" |
"Karar" | "Gerekce"). Karar degerleri: AL (uyarlayarak) / ALMA / BIZIMKI DAHA IYI. Satirlar:
- signature (duz SHA-256, anahtarsiz) | benchmark raporunda hash/imza YOK | AL (uyarlayarak) |
  fikir dogru ama duz SHA-256 zayif: tamper eden hash'i yeniden hesaplar; KASA'da HMAC
  (DPAPI-korumali vault anahtariyla) yapilmali — anahtarsiz malware gecerli etiket uretemez.
- expires_at (sabit 7 gun) | L4 drift-canary (ortam degisince re-run) | BIZIMKI DAHA IYI |
  takvim-suresi keyfi: 7 gun icinde ortam degisirse sertifika yalan soyler, degismezse bosuna
  expire olur; drift-canary tam dogru anda gecersiz kilar.
- overall_score 9/10 (ortalama skor) | verdict: tek kritik FAIL -> "YAYINA HAZIR DEGIL" | BIZIMKI
  DAHA IYI | ortalama kritigi gizler: 9/10 alan skill'in tek eksigi kritik bir acik olabilir;
  KASA'nin ikili verdict'i kritik bulguyu asla sulandirmaz.
- risk_breakdown + layer_details (bulgu SAYILARI) | 21 kontrolun tek tek PASS/FAIL/WARN/SKIP +
  severity | BIZIMKI DAHA IYI | sayim ("3 semgrep bulgusu") hangi bulgu oldugunu soylemez;
  kontrol-basina sonuc + severity aksiyon alinabilir.
- verification_url (public dogrulama API) | yok; yerel dogrulama | ALMA | private vault'un
  yabanciya kanit sunma ihtiyaci yok; public endpoint gereksiz saldiri yuzeyi.
- _summary.json (10978 skill agregasi) | yok | ALMA | N=1 urun icin agrega istatistik anlamsiz.
- mandate ledger (her transaction git commit) | AuditChain (hash-zinciri) | BIZIMKI DAHA IYI /
  esdeger | ikisi de append-only tamper-evidence; AuditChain zaten var, git'e tasimak kazanc degil.
- auditor + layers_run (hangi katman kostu) | STAMP (commit/config-hash/webview2/os-build/tier) |
  ESDEGER (bizimki daha zengin ortam-kokeni) | ikisi de provenance; STAMP ortami da baglar.
- gVisor sandbox (L2.5) | yok (untrusted 3P kod calistirmiyoruz) | ALMA (simdilik) | asagida bolum 5.

3. TEHDIT-MODELI UYUMU:
MarketNow'un problemi: yabancilarin yazdigi 10978 skill'i, yabancilara "guvenli" diye satmak.
Bu yuzden: public verification API (yabanci dogrulasin), expires_at (bayat sertifika riskini
takvimle sinirla), ortalama skor (10978 ogeyi triage etmek icin siralama metrigi), sandbox
(untrusted kod calistirma zorunlulugu). KASA'nin problemi: owner'in KENDI kodunun, KENDI
makinesinde, local malware/bulut-sync dusmanina karsi durumunu owner'a raporlamak. Yabanci yok,
untrusted kod yok, N=1. Dolayisiyla o dort desen (sandbox, public API, expires_at, ortalama skor)
tehdit-modeli uyusmazligi nedeniyle TRANSFER EDILMEZ. Kiyasin dogru okumasi: "onlar kotu" degil,
"farkli problem cozuyorlar".

4. ALINMAYA DEGER TEK SEY — benchmark raporunu "sertifika"lastirmak:
Sentinel'in dogru fikri: denetim ciktisini alanlari sabit, makine-dogrulanabilir, butunlugu
etiketli TEK ARTIFACT yapmak. KASA'daki bosluk: benchmark v2 raporu STAMP tasiyor ama results'in
hash'i/imzasi yok — sonradan degistirilse fark edilmez. Oneri: (a) results'i canonical JSON'a
indirger (deterministik siralama), (b) canonical-hash (SHA-256) hesapla, (c) mevcut STAMP ile
birlestir, (d) DPAPI-korumali vault anahtariyla HMAC'le (DUZ SHA-256 DEGIL — Sentinel'in zayifligi
tam bu: anahtarsiz hash'i tamper eden yeniden hesaplar; HMAC'te anahtar DPAPI arkasinda oldugundan
ayni-kullanici-DISI dusmanlar ve bulut-kopya senaryosu gecerli etiket uretemez). Neden dogal uzanti:
v2-STAMP zaten provenance topluyor, AuditChain zaten hash-zinciri/tamper-evidence ilkesini kurmus,
DPAPI anahtar altyapisi L2'de zaten var — yeni ilkel yok, uc mevcut parcanin birlesimi. Istenirse
sertifika ozeti AuditChain'e kayit olarak da eklenebilir (rapor, zincire baglanmis olur).
DURUST SINIR: ayni-kullanici malware DPAPI'yi cagirabildigi icin HMAC de ona karsi mutlak degil —
bu KASA tehdit modelindeki bilinen reziduel sinirin aynisi, yeni bir zayiflik degil.

5. REDDEDILENLER + NEDEN (her biri kisa madde):
- Ortalama skor: kritigi gizler; verdict ikiligi (YAYINA HAZIR / DEGIL) korunmali.
- expires_at: takvim keyfi; L4 drift-canary olay-tetiklemeli ve daha dogru.
- Public verification API: private vault'a yanlis desen; kanit tuketicisi yalnizca owner.
- gVisor sandbox: untrusted-code problemi bugun KASA'da yok. NOT DUS: Guardian action-layer veya
  ileride bir skill/marketplace entegrasyonu gundeme gelirse sandbox sorusu YENIDEN acilir;
  karar kapali, kapi isaretli.
- Ayrica genel bir supheci not: site anlatisi marketing-agirlikli; "6-nokta denetim" ve gVisor
  iddialarinin derinligi dogrulanamadi — MarketNow'dan desen alinirken uygulama kalitesi ornek
  alinmamali, yalnizca yapi fikri.

6. GUVEN SEVIYESI + NET ONERI:
- Guven seviyesi: yapisal analiz icin ORTA-YUKSEK (sertifika/agrega JSON alanlari birincil kanit,
  WebFetch ile goruldu); MarketNow'un uygulama KALITESI hakkinda DUSUK (site marketing-agirlikli,
  iddialar dogrulanamadi; tek anlik goruntu).
- YAP: benchmark-sertifikasi (canonical-hash + STAMP + DPAPI-anahtarli HMAC).
  KAR: rapor tamper-evident olur; brief'in butunluk cizgisiyle tutarli; drift-canary ile birlesince
  "gecerli + butunlugu dogrulanabilir" tek artifact. ZARAR/RISK: dusuk — yanlis anahtar yonetimi
  yapilirsa sahte guven hissi; ayni-kullanici malware reziduel siniri degismez. MALIYET: dusuk
  (mevcut DPAPI + hash altyapisi; kucuk bir modul + benchmark'a tek dikis).
- YAPMA: expires_at, ortalama skor, public verification API, gVisor (simdilik), agrega ozet.
  Gerekceler bolum 5'te.
- Net cumle: MarketNow'dan alinacak sey tek bir YAPI FIKRI (denetim ciktisinin butunluk-etiketli
  sertifikalasmasi); geri kalani farkli bir tehdit modelinin cozumleri.
"""

# ---------------------------------------------------------------------------
# CHECKLIST — qwen'in dogrulayacagi kabul kriterleri
# ---------------------------------------------------------------------------
CHECKLIST = """- [ ] Baslik tam olarak: MarketNow 'Sentinel' Sertifikalari vs KASA Guvenlik Yapisi — Karsilastirma Raporu (2026-07-09)
- [ ] 6 bolum SPEC sirasiyla var; markdown hiyerarsisi duzgun (tek #, bolumler ##)
- [ ] Bolum 2'de markdown TABLO var; kolonlar: Sentinel alani/deseni | KASA karsiligi | Karar | Gerekce; SPEC'teki 9 satirin hepsi mevcut
- [ ] Duz SHA-256 vs HMAC ayrimi dogru anlatilmis (anahtarsiz hash yeniden hesaplanabilir; HMAC anahtari DPAPI arkasinda)
- [ ] expires_at vs drift-canary kiyasi ve ortalama-skor-kritigi-gizler argumani acikca var
- [ ] Bolum 4'te 4-adimli oneri (canonical JSON -> canonical-hash -> STAMP -> DPAPI-anahtarli HMAC) ve ayni-kullanici-malware reziduel sinir DURUSTCE var
- [ ] Bolum 5'te gVisor reddine Guardian/marketplace GELECEK notu dusulmus
- [ ] Bolum 6'da guven seviyesi (yapisal: orta-yuksek; MarketNow kalitesi: dusuk) + YAP/YAPMA + kar/zarar/maliyet var
- [ ] Sayilar SPEC'tekiyle ayni (10978, 7 gun, 9/10, 21 kontrol, 0-10 histogram); SPEC'te olmayan sayi/API/dosya/olgu YOK
- [ ] Turkce prose; teknik terimler Ingilizce kalabilir; pazarlama dili yok, degerlendirme tonu durust
"""

DRAFT_PROMPT = (
    "You are a senior security engineer writing an evaluation report in TURKISH (Markdown).\n"
    "Follow the SPEC below EXACTLY: all 6 sections, in the given order, with proper markdown\n"
    "headings and the comparison TABLE in section 2 exactly as specified. Use ONLY the facts in\n"
    "the SPEC — do NOT invent numbers, APIs, file names, vendors or findings that are not in the\n"
    "SPEC. Technical terms and identifiers may stay in English. Tone: honest engineering\n"
    "assessment for the product owner, not marketing.\n"
    "Output ONLY the markdown document itself — no commentary, no code fences.\n\n"
    "=== SPEC ===\n" + SPEC
)


def build_review_prompt(draft_md: str) -> str:
    return (
        "You are reviewing a TURKISH markdown evaluation report against a CHECKLIST.\n"
        "The SPEC below is the ONLY ground truth. Fix every failing checklist item: add missing\n"
        "sections or table rows, fix heading hierarchy, delete any invented number/API/fact not\n"
        "present in the SPEC. Keep prose in Turkish; technical terms may stay in English.\n"
        "Improve wording where unclear but do not add new facts.\n"
        "Output ONLY the complete corrected markdown document — no commentary, no code fences.\n\n"
        "=== SPEC (ground truth) ===\n" + SPEC +
        "\n\n=== CHECKLIST ===\n" + CHECKLIST +
        "\n\n=== DRAFT ===\n" + draft_md
    )


def strip_fence(text: str) -> str:
    """Cikti ```markdown fence icine sarildiysa soy; degilse oldugu gibi birak."""
    t = text.strip()
    m = re.search(r"```(?:markdown|md)?\s*\r?\n(.*?)```", t, re.DOTALL)
    if m and len(m.group(1)) > 0.5 * len(t):
        return m.group(1).strip() + "\n"
    t = re.sub(r"^```(?:markdown|md)?\s*\r?\n", "", t)
    t = re.sub(r"\r?\n```\s*$", "", t)
    return t.strip() + "\n"


def main() -> None:
    if not ollama_up():
        print("HATA: Ollama ayakta degil (localhost:11434).", flush=True)
        sys.exit(1)

    review_only = "--review-only" in sys.argv

    if review_only:
        with open(OUT, "r", encoding="utf-8") as f:
            draft_md = f.read()
        print("[mode] review-only: mevcut rapor qwen'e veriliyor", flush=True)
        t_draft = 0.0
    else:
        t0 = time.time()
        draft_raw = call_model(DRAFTER, DRAFT_PROMPT, num_predict=6144)
        t_draft = time.time() - t0
        draft_md = strip_fence(draft_raw)
        print(f"[drafter] {DRAFTER}: {t_draft:.1f}s, {len(draft_md)} chars", flush=True)

    t1 = time.time()
    final_raw = call_model(REVIEWER, build_review_prompt(draft_md), num_predict=6144)
    t_review = time.time() - t1
    final_md = strip_fence(final_raw)
    print(f"[reviewer] {REVIEWER}: {t_review:.1f}s, {len(final_md)} chars", flush=True)

    if len(final_md.strip()) < 800:
        print("HATA: reviewer ciktisi supheli derecede kisa; dosya YAZILMADI.", flush=True)
        sys.exit(2)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(final_md)
    print(f"[out] {OUT} yazildi ({len(final_md)} chars; draft {t_draft:.0f}s + review {t_review:.0f}s)",
          flush=True)


if __name__ == "__main__":
    main()
