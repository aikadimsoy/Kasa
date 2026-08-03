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


def _detect_leaks(rec):
    """Bir kayittaki (pass==1 cold ya da pass==2 warmed) cok-katmanli parmak-izi
    sizintisini doner. KATMAN-TASIMA YOK (ilke-6): webgl (JS) / accept_language
    (HTTP<->JS) / timezone (JS) / platform (JS) kendi katmanlarinda denetlenir.
    evaluate() ve evaluate_cold() bu TEK kurali harfiyen paylasir; cold ile warmed
    arasinda kural farki olusmasin diye tek kaynakta tutulur."""
    js = rec.get("js", {}) or {}
    http = rec.get("http", {}) or {}
    leaks = []

    renderer = (js.get("webglRenderer") or "").lower()
    # KASA'nin kasten urettigi sahte GPU'lari leak sayma
    known_spoofs = [
        "intel(r) uhd graphics 620",
        "radeon rx 580",
        "geforce gtx 1660"
    ]
    if any(m in renderer for m in _GPU_MARKERS) and not any(s in renderer for s in known_spoofs):
        leaks.append("webgl")

    http_lang = (http.get("accept_language", "") or "").split(",")[0].strip().lower()
    js_lang = (js.get("language", "") or "").lower()
    if http_lang != js_lang:
        leaks.append("accept_language")

    if js.get("timezone") != "Europe/Berlin" or js.get("tzOffset") != _berlin_expected_offset():
        leaks.append("timezone")

    if js.get("platform") != "Win32":
        leaks.append("platform")

    return leaks


def evaluate(records):
    if not records:
        return False, {"boot_ok": False, "leaks": [], "sample": {}}

    # Tercihen pass==2 (pre-injection uygulanmis reload), yoksa son kayit.
    rec = None
    for r in records:
        if r.get("pass") == 2:
            rec = r
    if rec is None:
        rec = records[-1]

    leaks = _detect_leaks(rec)
    return (not leaks), {"boot_ok": True, "leaks": leaks, "sample": rec}


def evaluate_cold(records):
    """B1 KANITI (ilke-7): ISINMIS (pass==2) degil, COLD pass==1 uzerinden verdict.
    pass==1 = adversary_site'in pre-injection UYGULANMADAN ilk navigasyonda dondurdugu
    sayfa ('pre-inject yok, yaris'). Spoof'un ILK istekten ONCE inip inmedigini olcer.
    Warmed evaluate() ile AYNI _detect_leaks kuralini kullanir (ilke-6).
    Doner (ok, meta): meta.leaks bos => cold kimlik tutarli => B1 gecti.
    meta.blind True => cold kayit HIC yok => harness kor => ASLA PASS sayma (false-PASS avi)."""
    for r in records:
        if r.get("pass") == 1:  # ILK pass==1 = en erken cold gozlem
            leaks = _detect_leaks(r)
            return (not leaks), {"cold": True, "leaks": leaks, "sample": r, "blind": False}
    # pass==1 yok: cold veri yakalanmamis; PASS demek sessiz false-PASS olur.
    return False, {"cold": True, "leaks": [], "sample": {}, "blind": True}


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
