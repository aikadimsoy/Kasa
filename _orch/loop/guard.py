# -*- coding: utf-8 -*-
"""
KASA loop — guard + rollback. Mevcut pipeline'lardaki needle-guard + .bak desenini
tek yere toplar. Kotu bir splice'i ENGELLER: py_compile + must-have + forbidden kontrolu;
yedek al / geri yukle. loop_runner bunu her fix denemesinde kullanir.
"""
import os, shutil, time, py_compile, tempfile


def number_lines(text: str) -> str:
    """Returns the text with 1-based line numbers, e.g. "  42| import os".

    Modelin duzenlemeyi SATIR NUMARASIYLA gostermesi icin kullanilir. Numara okumak,
    metni bayt-bayt kopyalamaktan cok daha kolaydir; olcum gosterdi ki yerel modeller
    uzun bir kod parcasini birebir tekrar edemiyor (uydurma/tekil-olmama hatalari)."""
    lines = text.splitlines()
    width = len(str(len(lines)))
    return "\n".join("%*d| %s" % (width, i, line) for i, line in enumerate(lines, 1))


def _norm(s: str) -> str:
    """Bosluk-toleransli karsilastirma anahtari: satir sonu ve kenar bosluklari duser."""
    return "\n".join(x.strip() for x in s.strip().splitlines())


def apply_line_edits(original: str, edits) -> tuple:
    """Applies line-range edits: [{"start": int, "end": int, "new": str, "old": str?}].

    SEBEP: metin-cipali yamada model "old" degerini birebir uretemiyordu; olculdu ki
    duzenlemelerin cogu ya TEKIL DEGIL (ayni parca dosyada 6 kez geciyor) ya da UYDURMA
    (dosyada hic bulunmuyor) cikti. Satir araligi bu iki hatayi da yapisal olarak kaldirir:
    numara tekildir ve modelin metni tekrar etmesine gerek kalmaz.
    GUVENLIK: "old" verilirse o araligin MEVCUT icerigiyle (bosluk-toleransli) karsilastirilir;
    tutmazsa +-5 satirlik pencerede dogru yer aranir, o da yoksa TUM yama reddedilir.
    Cakisan araliklar reddedilir; uygulama ALTTAN USTE yapilir ki numaralar kaymasin."""
    if not edits:
        return False, "yama bos: model hic duzenleme uretmedi (ya da JSON ayristirilamadi)"
    lines = original.splitlines()
    n = len(lines)
    plan = []
    for i, edit in enumerate(edits, 1):
        try:
            start = int(edit["start"])
            end = int(edit.get("end", start))
        except (KeyError, TypeError, ValueError):
            return False, f"duzenleme {i}: 'start' (ve istege bagli 'end') tamsayi olmali"
        if not (1 <= start <= end <= n):
            return False, f"duzenleme {i}: satir araligi disarida ({start}-{end}, dosya {n} satir)"
        new = edit.get("new", "")
        if not isinstance(new, str):
            return False, f"duzenleme {i}: 'new' metin olmali"
        old = edit.get("old")
        if isinstance(old, str) and old.strip():
            want = _norm(old)
            have = _norm("\n".join(lines[start - 1:end]))
            if want != have:
                # Model numarayi kacirmis olabilir: yakin pencerede dogru yeri ara.
                # AMA pencerede BIRDEN FAZLA eslesme varsa duzeltme YAPILMAZ. Sebep: bu
                # dosyada '"status": "FAIL",' gibi satirlar tekrar ediyor; tek eslesmeyi
                # secmek sessizce YANLIS satiri degistirmek olurdu. Belirsizlikte susup
                # yanlis yapmaktansa gurultuyle reddetmek yeglenir.
                span = end - start + 1
                found = [s for s in range(max(1, start - 5), min(n - span + 1, start + 5) + 1)
                         if _norm("\n".join(lines[s - 1:s + span - 1])) == want]
                if not found:
                    return False, (f"duzenleme {i}: {start}-{end} satirlarinin icerigi "
                                   f"'old' ile uyusmuyor ve yakinda da bulunamadi")
                if len(found) > 1:
                    return False, (f"duzenleme {i}: satir {start} tutmadi ve yakinda "
                                   f"{len(found)} olasi yer var ({found}) - belirsiz, "
                                   f"model dogru numarayi vermeli")
                start, end = found[0], found[0] + span - 1
        plan.append((start, end, new))

    plan.sort(key=lambda p: p[0])
    for a, b in zip(plan, plan[1:]):
        if b[0] <= a[1]:
            return False, f"duzenlemeler cakisiyor: {a[0]}-{a[1]} ile {b[0]}-{b[1]}"

    out = list(lines)
    for start, end, new in reversed(plan):
        out[start - 1:end] = new.splitlines() if new else []
    text = "\n".join(out)
    if original.endswith("\n"):
        text += "\n"
    if text == original:
        return False, "yama uygulandi ama dosya degismedi"
    return True, text


def apply_edits(original: str, edits) -> tuple:
    """Applies a list of {"old", "new"} edits to `original`. Returns (ok, result_or_reason).

    Her duzenleme icin uc sart aranir ve HERHANGI biri bozulursa TUM yama reddedilir
    (kismi uygulama yok - dosya ya tam istenen hale gelir ya hic degismez):
      1. "old" bos olamaz ve "new"den farkli olmalidir; aksi halde model bos is yapmistir.
      2. "old" dosyada TAM OLARAK BIR KEZ gecmelidir. Sifir kez geciyorsa model metni
         uydurmus/degistirmis demektir; birden fazla geciyorsa hangi yerin kastedildigi
         belirsizdir ve yanlis satiri degistirme riski dogar.
      3. Degisiklikler SIRAYLA uygulanir; her adimda arama guncel metinde yapilir, boylece
         onceki bir duzenlemenin urettigi metin uzerinde de calisilabilir.
    Dokunulmayan her bayt aynen kalir - yorumlarin korunmasi bu yuzden garantidir."""
    if not edits:
        return False, "yama bos: model hic duzenleme uretmedi (ya da JSON ayristirilamadi)"
    text = original
    for i, edit in enumerate(edits, 1):
        old, new = edit.get("old", ""), edit.get("new", "")
        if not isinstance(old, str) or not isinstance(new, str) or not old:
            return False, f"duzenleme {i}: 'old'/'new' metin olmali ve 'old' bos olamaz"
        if old == new:
            return False, f"duzenleme {i}: 'old' ile 'new' ayni - bos is"
        hits = text.count(old)
        if hits == 0:
            return False, (f"duzenleme {i}: aranan metin dosyada YOK "
                           f"(model birebir kopyalamamis): {old[:70]!r}")
        if hits > 1:
            return False, (f"duzenleme {i}: aranan metin {hits} kez geciyor, TEKIL degil - "
                           f"hangi yer oldugu belirsiz: {old[:70]!r}")
        text = text.replace(old, new, 1)
    if text == original:
        return False, "yama uygulandi ama dosya degismedi"
    return True, text


def _comment_lines(code: str) -> int:
    """Counts explanatory lines: standalone comments plus docstring/body text.

    TURKCE NOT: 'aciklama' = yorum satiri + docstring govdesi. Kaba ama kararli bir olcut;
    amac yuzde-hassasiyet degil, TOPLU SILINMEYI yakalamak."""
    n, in_doc, delim = 0, False, ""
    for raw in code.splitlines():
        s = raw.strip()
        if in_doc:
            n += 1
            if delim in s:
                in_doc = False
            continue
        if s.startswith("#"):
            n += 1
            continue
        for d in ('"""', "'''"):
            if s.startswith(d) or s.startswith("r" + d):
                n += 1
                body = s.split(d, 1)[1]
                if d not in body:          # ayni satirda kapanmiyorsa cok-satirli
                    in_doc, delim = True, d
                break
    return n


def check_candidate(code: str, guard_needles, forbidden_needles,
                    original: str = None, min_comment_ratio: float = None):
    """(ok: bool, reason: str). Once py_compile, sonra needle kontrolleri, sonra aciklama orani.

    guard_needles: hepsi BULUNMALI. forbidden_needles: hicbiri BULUNMAMALI.

    SEBEP (2026-08-01, olculdu): needle'lar KODUN YAPISINI korur, BILGIYI korumaz.
    checks/scan.py isinde model testi gecirdi, tum needle'lari sagladi -> guard KABUL etti;
    ama Turkce gerekce notlarini toplu sildi: 'sahte PASS=0' dersini (neden --all-files
    zorunlu), fail-closed allowlist gerekcesini, _ARCHIVE_MAX kor-nokta aciklamasini.
    SONUC (fixlenmezse): bu depoda deger kodun kendisi kadar 'neden'dedir (KOD EN + TR-NOT
    kurali). Her sifir-token turu bu bilgiyi biraz daha asindirir ve KIMSE fark etmez —
    testler yesil kalir. Sessiz bilgi kaybi, sessiz kod hatasindan daha pahalidir cunku
    geri getirilemez.
    KARAR: aciklama satiri sayisi is-basina bir esigin altina DUSEMEZ. Opsiyonel (parametre
    verilmezse davranis aynen eskisi gibi) -> mevcut isler etkilenmez."""
    fd, tmp = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            py_compile.compile(tmp, doraise=True)
        except py_compile.PyCompileError as e:
            return False, f"py_compile HATA: {e}"
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    for n in (guard_needles or []):
        if n not in code:
            return False, f"eksik needle: {n!r}"
    for n in (forbidden_needles or []):
        if n in code:
            return False, f"yasak needle mevcut: {n!r}"
    if original is not None and min_comment_ratio:
        before, after = _comment_lines(original), _comment_lines(code)
        floor = before * float(min_comment_ratio)
        if after < floor:
            return False, (f"aciklama kaybi: {before} -> {after} satir "
                           f"(taban {floor:.0f}, oran {min_comment_ratio}); "
                           f"TR gerekce notlari silinmis")
    return True, "ok"


_BAK_DIR = "d:/kasa/_bak_archive"
_BAK_KEEP = 10  # basename basina TUTULACAK son yedek sayisi (SINIRLI SINK -> retention)


def _prune(base: str) -> None:
    """base icin _bak_archive'da son _BAK_KEEP yedegi tut, eskiyi sil. Timestamp lexical=kronolojik
    oldugundan sirali dilimleme dogru. Bu, 'merkezi dizine tasidik ama sinirsiz birikiyor' kor
    noktasini kapatir: sink artik BOUNDED."""
    prefix = base + ".bak_loop_"
    baks = sorted(f for f in os.listdir(_BAK_DIR) if f.startswith(prefix))
    for old in baks[:-_BAK_KEEP]:
        try:
            os.remove(os.path.join(_BAK_DIR, old))
        except OSError:
            pass


def backup(path: str) -> str:
    """path'i _bak_archive/<ad>.bak_loop_<ts> olarak yedekler; yedek yolunu dondurur.
    KOK-NEDEN (iki katman): (a) yedek kaynak dizinine DEGIL merkezi arsive yazilir; (b) loop her
    iterasyonda uretir -> SINIRSIZ SINK olmasin diye basename basina son _BAK_KEEP tutulur, gerisi
    age-out. 'Nereye' degil 'ne kadar' da sinirli. Arsiv ayrica SCAN-BAK-HYGIENE'de sayi-esigiyle
    denetlenir (retention bozulursa musfettis WARN basar -> kor nokta yok)."""
    os.makedirs(_BAK_DIR, exist_ok=True)
    base = os.path.basename(path)
    bak = os.path.join(_BAK_DIR, base + ".bak_loop_" + time.strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(path, bak)
    _prune(base)
    return bak


def restore(path: str, bak: str) -> None:
    """Yedegi geri yukler (rollback)."""
    shutil.copy2(bak, path)


def write(path: str, code: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()
