# -*- coding: utf-8 -*-
"""
gen_threat_model.py — SIFIR-TOKEN orkestrasyon (yalnizca boru hatti).
deepseek taslak -> qwen inceleme -> d:\\kasa\\docs\\THREAT_MODEL.md
Prose YEREL modellerden gelir; bu dosya icerik uretmez, SPEC'i tasir ve ciktiyi yazar.
Calistirma:
  python gen_threat_model.py            (tam tur: deepseek + qwen)
  python gen_threat_model.py --review-only  (mevcut THREAT_MODEL.md'yi qwen'e yeniden incelet)
"""
import sys, re, time

sys.path.insert(0, r"d:\kasa\_orch\loop")
from model_pipe import call_model, DRAFTER, REVIEWER, ollama_up

OUT = r"d:\kasa\docs\THREAT_MODEL.md"

# ---------------------------------------------------------------------------
# SPEC — faktuel iskelet (sef tarafindan verilen; modeller bunun disina cikamaz)
# ---------------------------------------------------------------------------
SPEC = """Baslik: "KASA Guvenlik Katmani — Tehdit Modeli (THREAT_MODEL v1)"

Belge TURKCE yazilacak; kod/terimler (DPAPI, AES-GCM, SQLCipher, MCP, WHERE/LIKE/FTS vb.) Ingilizce kalabilir.
Asagidaki 8 bolum, bu sirayla, duzgun markdown baslik hiyerarsisiyle (#, ##, ###) yer almali.

1. AMAC & KAPSAM:
KASA = local-first sifreli hafiza kasasi + MCP server + gizlilik-tarayicisi + yerel modeller.
Bu belge guvenlik-katmani projesinin (L0–L4) dusman tanimidir; tum kontroller buradan gerekcelenir.

2. DORT DUSMAN SINIFI (her biri ayri alt-baslik: yetenekleri, hedefi, KASA'nin savunmasi):
(A) Ayni-kullanici yerel malware — kullanicinin kendi OS oturumunda calisan kotu yazilim.
    DPAPI'yi cagirabilir (ayni kullanici baglami oldugu icin). Savunma sinirlidir; bu bilincli
    bir REZIDUEL risktir, gizlenmez.
(B) Diger OS hesaplari — ayni makinedeki baska kullanicilar. Owner-only ACL + DPAPI
    (anahtar makine+kullaniciya bagli) onlari durdurur.
(C) Bulut-sync / OneDrive — kasa.db bulut klasorundeyse duz metin kopyalanir. At-rest
    sifreleme (L2) bunu kapatir: DPAPI anahtari makine+kullaniciya bagli oldugundan bulut
    kopya baska yerde ACILAMAZ.
(D) Sayfa enjeksiyonu / kotu web icerigi — tarayiciya enjekte olan JS, fingerprint sizintisi,
    veri/komut karismasi. Savunma: fingerprint tutarliligi (L3 B1/B4) + veri-komut ayrimi.

3. REZIDUEL RISKLER (DURUST — "kabul edilmis" dili, gizlenmis degil; en az su 4 madde):
- Ayni-kullanici malware DPAPI'yi cagirabilir (dusman A ile ortusen bilincli sinir).
- Bellekteki duz metin swap/hibernate ile pagefile'a dusebilir — Python'da pratik mitigasyon yok.
- profile.provenance (event-ID referanslari) L2'de plaintext kalir → hangi olaylardan
  turedigi gorulebilir (linkage sizintisi); dusuk hassasiyet + sicak-yol maliyeti gerekcesiyle kabul.
- Sorgulanan metadata kolonlari (profile.key, events.ttl_expiry/distilled/source,
  audit.timestamp/agent_id/action/*_hash, permissions.*) L2'de plaintext kalir — sorgu/indeks/
  hash-zinciri bunlara bagli; bilincli sinir.

4. L2 AT-REST KARARI OZETI (ayri baslik):
Neden hibrit app-layer AES-GCM, neden SQLCipher DEGIL: bu makinede SQLCipher wheel yok +
C derleyici yok (infeasible) ve ampirik olarak gereksiz (icerik kolonunda tek yapisal filtre
forget()'in soguk-yol LIKE'i). Sifrelenen kolonlar: profile.value, events.content, audit.details.
forget() decrypt-scan'e, audit encrypt-then-hash'e yeniden tasarlanir.

5. SQLCIPHER TRIPWIRE (ayri baslik):
Ileride herhangi bir sorgu content kolonu uzerinde WHERE/LIKE/FTS gerektirirse, app-layer
karari yeniden acilir (SQLCipher veya blind-index masaya doner). Karar kapali, kapi isaretli.

6. DPAPI TASINABILIRLIK:
DPAPI Windows-only. Anahtar temini KeyProvider dikisi arkasinda; macOS portunda Keychain
provider gerekir (simdi yazilmaz, YAGNI).

7. ILKE: "SIFRELEMEDEN ONCE SORGUYU LISTELE":
Bir kolonu sifrelemek depolama degil erisim-deseni karardir; kolona dokunan HER SQL ifadesi
(WHERE/LIKE/JOIN/ORDER/hash-zinciri/audit-log) once listelenmeli. Bu ilke, forget() ve audit
yan-kanalinin nasil kacirildiginin dersidir.

8. KAPSAM DISI:
Ag MITM, fiziksel erisim, Guardian G1 action-layer (asagi-akis).
"""

# ---------------------------------------------------------------------------
# CHECKLIST — qwen'in dogrulayacagi kabul kriterleri
# ---------------------------------------------------------------------------
CHECKLIST = """- [ ] Dort dusman sinifi A/B/C/D ayri ayri alt-basliklarda, her biri yetenek + hedef + savunma ile
- [ ] Reziduel riskler bolumu, en az 4 madde, "kabul edilmis" dili (gizleme yok)
- [ ] L2 hibrit karari ve SQLCipher tripwire AYRI basliklar halinde
- [ ] DPAPI Windows-only + KeyProvider/Keychain notu var
- [ ] "Sifrelemeden once sorguyu listele" ilkesi ayri bolum olarak var
- [ ] Kapsam-disi bolumu var (ag MITM, fiziksel erisim, Guardian G1 action-layer)
- [ ] Turkce prose; markdown baslik hiyerarsisi duzgun (tek # baslik, ## bolumler)
- [ ] SPEC'te olmayan uydurma API/dosya adi/olgu YOK (yalniz verilen faktuel iskelet)
- [ ] Belge basligi tam olarak: KASA Guvenlik Katmani — Tehdit Modeli (THREAT_MODEL v1)
"""

DRAFT_PROMPT = (
    "You are a security engineer writing a threat-model document in TURKISH (Markdown).\n"
    "Follow the SPEC below EXACTLY: all 8 sections, in the given order, as proper markdown\n"
    "headings. Use ONLY the facts in the SPEC — do NOT invent APIs, file names, versions,\n"
    "libraries or mitigations that are not in the SPEC. Technical terms and code identifiers\n"
    "may stay in English. Write clear, honest prose (residual risks are ACCEPTED, not hidden).\n"
    "Output ONLY the markdown document itself — no commentary, no code fences.\n\n"
    "=== SPEC ===\n" + SPEC
)


def build_review_prompt(draft_md: str) -> str:
    return (
        "You are reviewing a TURKISH markdown threat-model document against a CHECKLIST.\n"
        "The SPEC below is the ONLY ground truth. Fix every failing checklist item: add missing\n"
        "sections, fix heading hierarchy, delete any invented API/file/fact not present in the\n"
        "SPEC. Keep prose in Turkish; technical terms may stay in English. Improve wording where\n"
        "unclear but do not add new facts.\n"
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
        print("[mode] review-only: mevcut THREAT_MODEL.md qwen'e veriliyor", flush=True)
        t_draft = 0.0
    else:
        t0 = time.time()
        draft_raw = call_model(DRAFTER, DRAFT_PROMPT, num_predict=4096)
        t_draft = time.time() - t0
        draft_md = strip_fence(draft_raw)
        print(f"[drafter] {DRAFTER}: {t_draft:.1f}s, {len(draft_md)} chars", flush=True)

    t1 = time.time()
    final_raw = call_model(REVIEWER, build_review_prompt(draft_md), num_predict=4096)
    t_review = time.time() - t1
    final_md = strip_fence(final_raw)
    print(f"[reviewer] {REVIEWER}: {t_review:.1f}s, {len(final_md)} chars", flush=True)

    if len(final_md.strip()) < 500:
        print("HATA: reviewer ciktisi supheli derecede kisa; dosya YAZILMADI.", flush=True)
        sys.exit(2)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(final_md)
    print(f"[out] {OUT} yazildi ({len(final_md)} chars; draft {t_draft:.0f}s + review {t_review:.0f}s)",
          flush=True)


if __name__ == "__main__":
    main()
