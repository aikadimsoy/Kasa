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


def backup(path: str) -> str:
    """path'i _bak_archive/<ad>.bak_loop_<ts> olarak yedekler; yedek yolunu dondurur.
    KOK-NEDEN FIX: yedek kaynak DIZININE degil MERKEZI arsive yazilir; aksi halde her loop
    iterasyonu _orch/loop'a bir .bak_loop birakip birikir (107 dosya olmustu). _bak_archive
    SCAN-BAK-HYGIENE'de haric tutulur ve gitignore'ludur -> sessiz birikim/izleme yok."""
    os.makedirs(_BAK_DIR, exist_ok=True)
    bak = os.path.join(_BAK_DIR, os.path.basename(path) + ".bak_loop_" + time.strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(path, bak)
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
