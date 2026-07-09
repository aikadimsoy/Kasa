# -*- coding: utf-8 -*-
"""
KASA loop — guard + rollback. Mevcut pipeline'lardaki needle-guard + .bak desenini
tek yere toplar. Kotu bir splice'i ENGELLER: py_compile + must-have + forbidden kontrolu;
yedek al / geri yukle. loop_runner bunu her fix denemesinde kullanir.
"""
import os, shutil, time, py_compile, tempfile


def check_candidate(code: str, guard_needles, forbidden_needles):
    """(ok: bool, reason: str). Once py_compile, sonra needle kontrolleri.
    guard_needles: hepsi BULUNMALI. forbidden_needles: hicbiri BULUNMAMALI."""
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
