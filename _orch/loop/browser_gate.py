# -*- coding: utf-8 -*-
"""KASA saglik kapisi: gercek tarayiciyi acar, adversary_site.py ile parmak-izi
sizintisini olcer. Otonom fix-loop bir fix'ten sonra bunu cagirir (browser_gate).

Mimari not: bu dosya motor/dogrulama katmanina aittir (pipeline+splice+verify izinli
bolge); evaluate() kurali kesin ve tek-dogru-cevapli oldugu icin elle yazilmistir."""
import calendar
import datetime
import json
import os
import subprocess
import sys

REPO = r"d:/kasa"
ADV_DIR = REPO + "/_orch/redteam"
CAPTURES = ADV_DIR + "/captures.jsonl"
ADV_URL = "http://127.0.0.1:8901/?pass=1"
PY = sys.executable

# Gercek GPU'yu ele veren belirtecler (buyuk/kucuk harf duyarsiz).
_GPU_MARKERS = ("rtx", "geforce", "radeon", "nvidia")


class _Adversary:
    """adversary_site.py'yi AYRI OS SURECI olarak tutar. Thread degil: modulun
    serve_forever() cagrisi bloklar ve httpd nesnesini disari vermez, dolayisiyla
    thread tabanli bir .stop() 8901 portunu serbest birakamaz (sonraki cagri
    OSError 10048 ile patlar). Ayri surec + terminate() bu tikanmayi onler."""

    def __init__(self, proc):
        self.proc = proc

    def stop(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        except Exception:
            pass


def start_adversary():
    proc = subprocess.Popen([PY, os.path.join(ADV_DIR, "adversary_site.py")], cwd=ADV_DIR)
    # Port'a baglanmasi icin kisa bir an taniyalim.
    import time
    time.sleep(1.0)
    return _Adversary(proc)


def launch_kasa(timeout_s):
    # captures.jsonl'i sifirla (parent yoksa olustur).
    os.makedirs(os.path.dirname(CAPTURES), exist_ok=True)
    open(CAPTURES, "w").close()

    env = os.environ.copy()
    env["KASA_HEALTHCHECK_URL"] = ADV_URL
    env["KASA_HEALTHCHECK_MS"] = str(max(1, timeout_s - 2) * 1000)

    proc = subprocess.Popen(
        [PY, "-c",
         "import sys;sys.path.insert(0,r'd:/kasa');"
         "from src.browser.browser_window import open_browser;open_browser()"],
        cwd=REPO, env=env,
    )
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()  # zombi/asili surec birakma


def read_captures():
    if not os.path.exists(CAPTURES):
        return []
    records = []
    with open(CAPTURES, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
    return records


def _berlin_expected_offset():
    """Europe/Berlin icin JS getTimezoneOffset()-tarzi beklenen deger (dk).
    Yaz saati (CEST) => -120, kis saati (CET) => -60. Tam DST kurali:
    Mart'in son Pazari <= bugun < Ekim'in son Pazari ise DST aktiftir."""
    now = datetime.datetime.now()
    year = now.year
    dom_march = 31 - ((calendar.weekday(year, 3, 31) + 1) % 7)
    dom_oct = 31 - ((calendar.weekday(year, 10, 31) + 1) % 7)
    start = datetime.date(year, 3, dom_march)
    end = datetime.date(year, 10, dom_oct)
    today = now.date()
    return -120 if (start <= today < end) else -60


def evaluate(records):
    if not records:
        return False, {"boot_ok": False, "leaks": [], "sample": {}}

    boot_ok = True
    # Tercihen pass==2 (pre-injection uygulanmis reload), yoksa son kayit.
    rec = None
    for r in records:
        if r.get("pass") == 2:
            rec = r
    if rec is None:
        rec = records[-1]

    js = rec.get("js", {}) or {}
    http = rec.get("http", {}) or {}
    leaks = []

    renderer = (js.get("webglRenderer") or "").lower()
    if any(m in renderer for m in _GPU_MARKERS):
        leaks.append("webgl")

    http_lang = (http.get("accept_language", "") or "").split(",")[0].strip().lower()
    js_lang = (js.get("language", "") or "").lower()
    if http_lang != js_lang:
        leaks.append("accept_language")

    if js.get("timezone") != "Europe/Berlin" or js.get("tzOffset") != _berlin_expected_offset():
        leaks.append("timezone")

    if js.get("platform") != "Win32":
        leaks.append("platform")

    return (not leaks), {"boot_ok": boot_ok, "leaks": leaks, "sample": rec}


def run_gate(mode="boot", timeout_s=16):
    """Tarayiciyi acar, olcer, degerlendirir. Hicbir istisna disari sizmaz."""
    try:
        adv = start_adversary()
        try:
            launch_kasa(timeout_s)
            records = read_captures()
            _, report = evaluate(records)
        finally:
            adv.stop()

        if mode == "fingerprint":
            ok = report["boot_ok"] and not report["leaks"]
        else:  # boot
            ok = report["boot_ok"]
        return ok, report
    except Exception as e:
        return False, {"error": str(e)}


if __name__ == "__main__":
    print(json.dumps(run_gate("fingerprint"), default=str, indent=2))
