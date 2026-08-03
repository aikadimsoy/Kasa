# -*- coding: utf-8 -*-
"""
Tarama kapsami kapisi: gizli-anahtar taramasi DERLEME CIKTISINI gezmemeli.

SEBEP (olculdu 2026-08-02): detect-secrets `--all-files` ile depoyu tariyordu ve depo
11.760 dosya / 3.776 MB. Bunun %95'i Nuitka derleme ciktisi (build_nuitka 6.514 dosya /
2.275 MB, build_nuitka_312 2.916 dosya, build_nuitka_onefile 1.762 dosya) -- yani .pyd/.dll
ikili dosyalari. Gercek kaynak toplam ~2 MB.
SONUC (duzeltilmezse) zincir soyle isliyordu:
  3,7 GB ikili gez -> 300 sn asilir -> TimeoutExpired -> "kritik acik" raporlanir.
Yani "guvenlik acigi" sanilan sey, aslinda derleme klasorunu taramaya calismakti.
2026-08-02'de timeout artik ERROR sayiliyor (belirti duzeldi) ama tarama HALA kosmuyor;
bu dosya kok nedeni kapatir: kapsam daralinca tarama saniyeler surer ve ILK KEZ gercek
bir cevap uretir.

NOT: derleme ciktisini haric tutmak bir kor nokta yaratmaz -- oradaki ikili dosyalar
kaynaktan uretilir; kaynakta secret varsa zaten kaynak taramasinda yakalanir.
"""
import re
import sys

import pytest

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _KASA_ROOT)

from tools.security_bench.checks import scan as scan_mod  # noqa: E402

# Taramanin ASLA gezmemesi gereken uretim-ciktisi dizinleri (olculdu: dosyalarin %95'i).
BUILD_DIRS = ["build_nuitka", "build_nuitka_312", "build_nuitka_onefile"]


class _Recorder:
    """Her subprocess.run cagrisinin komut satirini kaydeder."""

    def __init__(self):
        self.cmds = []

    def __call__(self, *args, **kwargs):
        self.cmds.append(list(args[0]) if args else [])

        class _Proc:
            returncode = 0
            stderr = ""
            stdout = '{"results": {}}'

        return _Proc()


@pytest.fixture()
def recorder(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(scan_mod.subprocess, "run", rec)
    return rec


def _secrets_cmd(rec):
    for cmd in rec.cmds:
        if any("detect_secrets" in str(c) for c in cmd):
            return cmd
    return None


def test_secret_scan_excludes_build_output(recorder):
    """Derleme dizinleri dislama desenine girmeli — yoksa tarama 3,7 GB gezer."""
    scan_mod.run()
    cmd = _secrets_cmd(recorder)
    assert cmd, "detect-secrets hic cagrilmadi"
    assert "--exclude-files" in cmd, "dislama bayragi yok"
    pattern = cmd[cmd.index("--exclude-files") + 1]
    missing = [d for d in BUILD_DIRS if not re.search(re.escape(d), pattern)]
    assert not missing, (
        "derleme dizinleri dislanmiyor: %s | mevcut desen: %s" % (missing, pattern))


def test_exclusion_pattern_is_valid_regex(recorder):
    """NEGATIF KONTROL: bozuk regex sessizce her seyi disleyip sahte-temiz uretebilir."""
    scan_mod.run()
    cmd = _secrets_cmd(recorder)
    pattern = cmd[cmd.index("--exclude-files") + 1]
    try:
        re.compile(pattern)
    except re.error as e:
        pytest.fail("dislama deseni gecersiz regex: %s (%s)" % (pattern, e))


def test_exclusion_does_not_swallow_source_tree(recorder):
    """NEGATIF KONTROL — EN ONEMLISI: dislama gercek kaynagi kapsamamali.
    Fazla genis bir desen ('.*' gibi) taramayi bosaltir ve PASS uretir; bu, kapatmaya
    calistigimiz sahte-temizin ta kendisi olurdu."""
    scan_mod.run()
    cmd = _secrets_cmd(recorder)
    pattern = cmd[cmd.index("--exclude-files") + 1]
    rx = re.compile(pattern)
    must_be_scanned = [
        "src/mcp_server/server.py",
        "src/vault/database.py",
        "tools/security_bench/checks/scan.py",
        "kasa.toml",
        "_orch/loop/loop_runner.py",
    ]
    swallowed = [p for p in must_be_scanned if rx.search(p)]
    assert not swallowed, (
        "dislama deseni GERCEK KAYNAGI da eliyor (sahte-temiz riski): %s" % swallowed)


def test_build_paths_actually_match_the_pattern(recorder):
    """Desenin gercek derleme yollarina UYDUGUNU dogrula — HER IKI AYIRICIYLA.

    SEBEP (2026-08-02, bu testin kendi hatasi): ilk surumu yalnizca EGIK CIZGILI ornekler
    kullaniyordu ve yesil yaniyordu; ama uretim Windows'ta yollar TERS EGIK CIZGILI gelir,
    desen eslesmiyordu ve dislama HIC calismiyordu. Tarama yine 3,7 GB gezip 351 saniyede
    zaman asimina dustu. Yani test, olctugunu sandigi seyi hic olcmemisti.
    SONUC: ornekler artik iki ayirici bicimini de icerir; biri kacarsa test kirmizi olur."""
    scan_mod.run()
    cmd = _secrets_cmd(recorder)
    pattern = cmd[cmd.index("--exclude-files") + 1]
    rx = re.compile(pattern)
    samples = [
        # POSIX bicimi
        "build_nuitka/nuitka_spike1.dist/_asyncio.pyd",
        "build_nuitka_312/kasa.dist/python312.dll",
        "build_nuitka_onefile/kasa_app.exe",
        # Windows bicimi — uretimde gelen bicim budur
        r"build_nuitka\nuitka_spike1.dist\_asyncio.pyd",
        r"build_nuitka_312\kasa.dist\python312.dll",
        r"build_nuitka_onefile\kasa_app.exe",
        # Basta './' veya '.\' onekiyle
        r".\build_nuitka\x.pyd",
        "./build_nuitka/x.pyd",
    ]
    unmatched = [p for p in samples if not rx.search(p)]
    assert not unmatched, "desen gercek derleme yollarini yakalamiyor: %s" % unmatched
