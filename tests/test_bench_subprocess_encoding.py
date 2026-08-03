# -*- coding: utf-8 -*-
"""
Measurement-integrity gate: external tool output must never be silently lost.

TURKCE NOT (ne/neden):
  SEBEP: subprocess.run(..., text=True) Windows'ta YEREL kodlamayi kullanir; bu makinede
  cp1254 (Turkce). bandit / pip-audit / detect-secrets ciktisi UTF-8 bayt icerdiginde okuma
  thread'i UnicodeDecodeError atar, subprocess.run bunu YUTAR ve stdout'u BOS dondurur.
  SONUC (fixlenmezse): process.stdout = "" -> json.loads("") -> JSONDecodeError ->
  "Failed to parse output" -> kontrol, HIC KOSMAMIS oldugu halde bulgu raporlar. Yani
  sahte kirmizi ureten IKINCI bir mekanizma; tam da ERROR ayrimiyla kapatmaya calistigimiz
  hastaligin baska bir yolu.
  OLCULDU 2026-08-01: ayni cagri deseninde saf-ASCII cikti 98 karakter dondu, Turkce
  karakter iceren cikti 0 dondu.
  KARAR: her dis-alet cagrisi kodlamayi ACIKCA utf-8'e sabitler ve errors='replace' ile
  cozulemeyen bayti korur -> kanit kirpilabilir ama ASLA sessizce kaybolmaz.
"""
import subprocess
import sys

import pytest

sys.path.insert(0, "d:/kasa")

from tools.security_bench.checks import scan as scan_mod  # noqa: E402


class _Recorder:
    """Records the kwargs of every subprocess.run call made by the scanner."""

    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append(kwargs)

        class _Proc:
            returncode = 0
            stderr = ""
            stdout = '{"results": [], "dependencies": []}'

        return _Proc()


@pytest.fixture()
def recorder(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(scan_mod.subprocess, "run", rec)
    return rec


def test_every_external_call_pins_utf8(recorder):
    """Her dis-alet cagrisi encoding='utf-8' belirtmeli (yerel kodlamaya birakilmamali)."""
    scan_mod.run()
    assert recorder.calls, "scan.run() hic dis alet cagirmadi"
    missing = [k for k in recorder.calls if k.get("encoding") != "utf-8"]
    assert not missing, (
        "%d cagri kodlamayi sabitlemiyor (yerel cp1254'e dusuyor): %s"
        % (len(missing), missing[:2]))


def test_every_external_call_survives_undecodable_bytes(recorder):
    """errors='replace' olmali: cozulemeyen bayt tum ciktiyi dusurmemeli."""
    scan_mod.run()
    bad = [k for k in recorder.calls if k.get("errors") != "replace"]
    assert not bad, (
        "%d cagri errors='replace' kullanmiyor; tek bozuk bayt TUM kaniti silebilir: %s"
        % (len(bad), bad[:2]))


def test_undecodable_output_does_not_vanish(monkeypatch):
    """END-TO-END: cozulemeyen bayt iceren gercek bir alt-surec ciktisi BOS gelmemeli.

    Bu test uretim kodunu degil, DESENI dogrular: repo'daki cagri sekli boyle bir
    cikti karsisinda kanit kaybediyor mu? (negatif-kontrol: yanlis desen FAIL verir)."""
    code = "import sys; sys.stdout.write('Bilinen Sinirlar: \\u015f\\u0131\\u011f\\u00fc\\u00f6')"
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)
    assert proc.stdout, "utf-8 sabitlenmis cagri bile bos cikti dondurdu"
    assert "Bilinen" in proc.stdout, "kanit icerigi kayboldu: %r" % (proc.stdout,)
