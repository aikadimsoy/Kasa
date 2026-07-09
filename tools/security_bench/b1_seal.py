# -*- coding: utf-8 -*-
"""B1 MUHUR KAPISI — muhur bir insan karari DEGIL, uc AMPIRIK sinyalin yan urunudur.

Oturum dersi (kontrolor mekanik kurali): canli/ampirik olcum yapilmadan bir artefakt "hardened"
adini TASIYAMAZ. Bu yuzden "hardened" tag'ini bir insan atmaz; bu harness, uc sinyal de yesil
oldugunda muhru (docs/B1_SEAL.json + tag) KENDISI dusurur:

  1. cold_pass1_clean   : evaluate_cold(pass==1) canli cold-kosumda sizinti yok
                          (mock degil, gercek WebView2 -> spoof ILK istekten once indi).
  2. no_rogue_listener  : launch sonrasi localhost'ta d:/kasa'yi servis eden HICBIR dinleyici yok
                          (about:blank->html= regresyon kanit; kod-inanci degil, port-probe).
  3. watchdog_ok        : ilk navigasyon bu makinede makul surede gerceklesti (asili pencere yok).

seal_decision() ve _serves_kasa() GUI'siz test edilir (tests/test_b1_seal.py). run_live_seal()
canli WebView2 + owner-mevcudiyeti ister; sinyalleri gercek motordan toplar.
"""
import json
import os
import re
import subprocess
import sys
import time

REPO = r"d:/kasa"
SEAL_PATH = REPO + "/docs/B1_SEAL.json"


# ---- (2) AMPIRIK localhost-acik probe'u (kod-inanci DEGIL, gercek soket) ----------------

def _serves_kasa(host, port, sentinel_name, sentinel_head, timeout=0.4):
    """host:port'ta, d:/kasa'dan `sentinel_name` dosyasini SERVIS eden bir HTTP dinleyici var mi?
    GET /<sentinel> gercek dosyanin ilk baytlarini donerse -> rogue-server AYAKTA (acik kaniti)."""
    import http.client
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", "/" + sentinel_name.lstrip("/"))
        resp = conn.getresponse()
        body = resp.read(256)
        conn.close()
        return resp.status == 200 and sentinel_head[:32] in body
    except Exception:
        return False


def _list_listening_ports(host="127.0.0.1"):
    """localhost'ta LISTEN durumundaki TCP portlari (netstat -ano). BASARISIZSA EXCEPTION firlatir
    (yutup [] DONMEZ): sessiz [] = 'dinleyici yok' sahte-temizligi = tam da onlemek istedigimiz
    'olculemedi -> PASS' hatasi. Caller exception'i None (olculemedi) sinyaline cevirir."""
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                         capture_output=True, text=True, timeout=6)
    if out.returncode != 0:
        raise RuntimeError(f"netstat rc={out.returncode}")
    ports = set()
    for line in out.stdout.splitlines():
        if "LISTENING" not in line:
            continue
        for p in re.findall(r"(?:127\.0\.0\.1|0\.0\.0\.0|\[::1?\]):(\d+)\b", line):
            ports.add(int(p))
    return sorted(ports)


def rogue_listener_signal(root=REPO, host="127.0.0.1"):
    """no_rogue_listener sinyali (UC-DEGERLI):
      True  = TUM LISTEN portlari tarandi, d:/kasa servis eden YOK (about:blank->html= kaniti)
      False = d:/kasa servis eden bir dinleyici BULUNDU (acik ayakta)
      None  = OLCULEMEDI (netstat/probe patladi ya da sentinel yok) -> gate RED
    'Bildigim portta yok' DEGIL: netstat ile TUM LISTEN portlari taranir (efemeral port kacmaz)."""
    sentinel = ".gitignore"  # d:/kasa'da kesin var, hassas degil; servis edilirse cwd-acik demek
    p = os.path.join(root, sentinel)
    if not os.path.exists(p):
        return None  # OLCULEMEDI
    try:
        with open(p, "rb") as f:
            head = f.read(64)
        ports = _list_listening_ports(host)
    except Exception:
        return None  # OLCULEMEDI != temiz (ilke-11)
    return not any(_serves_kasa(host, port, sentinel, head) for port in ports)


# ---- DETERMINISTIK muhur kapisi (ilke-11: son soz kuralda, modelde/insanda degil) --------

def seal_decision(cold_pass1_clean, no_rogue_listener, watchdog_ok):
    """UNKNOWN != PASS (ilke-11 kok mesaji, muhur katmaninda). Her sinyal UC-DEGERLI:
      True  = olculdu, YESIL
      False = olculdu, KIRMIZI (gercek sizinti/rogue/timing)
      None (ya da True-OLMAYAN her sey) = OLCULEMEDI -> KIRMIZI
    Bir probe patlar / arac kosmaz / evaluate_cold timeout olursa sinyal None gelir ve muhur
    DUSMEZ (SCAN-SECRETS 'arac kosmadi -> sahte 0' hatasinin tekrari onlenir). SADECE ucu de
    STRICT True ise SEALED (truthy-coercion yok: 1/'yes' PASS saymaz). olculdu-kirmizi ve
    olculemedi AYRI raporlanir. Muhru INSAN degil BU KURAL verir."""
    checks = [
        (cold_pass1_clean, "cold_pass1_leak", "cold_pass1_unmeasured"),
        (no_rogue_listener, "rogue_localhost_server", "rogue_probe_unmeasured"),
        (watchdog_ok, "watchdog_timing", "watchdog_unmeasured"),
    ]
    reasons = []
    for val, measured_red, unmeasured in checks:
        if val is True:
            continue
        reasons.append(measured_red if val is False else unmeasured)
    return ("SEALED" if not reasons else "NOT_SEALED"), reasons


def write_seal(signals, status, reasons):
    """Muhur artefakti (durum + ham sinyaller + damga). SEALED ise B1 kanitlanmis demektir."""
    rec = {
        "artifact": "B1-cold-session",
        "status": status,
        "reasons": reasons,
        "signals": signals,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    os.makedirs(os.path.dirname(SEAL_PATH), exist_ok=True)
    with open(SEAL_PATH, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    return rec


# ---- Canli orkestrasyon (KAPI-2: gercek WebView2 + owner-mevcudiyeti; burada KOSULMAZ) ----

def run_live_seal(timeout_s=18):
    """CANLI: tarayiciyi cold acar, uc sinyali GERCEK motordan toplar, seal_decision uygular ve
    SEALED ise muhru (B1_SEAL.json + 'L3-B1-sealed' tag) DUSURUR. Owner-mevcudiyeti ister; GUI acar.
    NOT: bu fonksiyonun kendisi mock'lanamaz -> yesil ancak GERCEK cold-kosumdan gelir."""
    sys.path.insert(0, REPO + "/_orch/loop")
    import browser_gate as bg

    t0 = time.time()
    adv = bg.start_adversary()
    no_rogue = None
    try:
        # launch sirasinda port-probe: d:/kasa servis eden dinleyici var mi? (True/False/None)
        import threading
        sig = {"no_rogue": None}

        def _probe():
            time.sleep(3.0)  # WebView2 + (varsa) sunucu ayaga kalksin
            sig["no_rogue"] = rogue_listener_signal()

        pt = threading.Thread(target=_probe, daemon=True)
        pt.start()
        bg.launch_kasa(timeout_s)
        pt.join(timeout=2)
        no_rogue = sig["no_rogue"]
    finally:
        adv.stop()

    # cold + watchdog: OLCULEMEDI durumlari None (ilke-11: unknown != PASS, sahte-yesil olmaz).
    cold, cold_meta, watchdog_ok = None, {}, None
    try:
        records = bg.read_captures()
    except Exception as e:
        records, cold_meta = None, {"error": f"read_captures:{e}"}
    if records:
        try:
            cold_ok, cold_meta = bg.evaluate_cold(records)
            cold = bool(cold_ok)
        except Exception as e:
            cold, cold_meta = None, {"error": f"evaluate_cold:{e}"}
        watchdog_ok = True  # kayit geldi -> ilk-nav gerceklesti (pencere asili kalmadi)
    else:
        cold_meta = cold_meta or {"error": "kayit yok (WebView2 kosmadi?)"}  # cold/watchdog None

    signals = {
        "cold_pass1_clean": cold,
        "cold_meta": cold_meta,
        "no_rogue_listener": no_rogue,
        "watchdog_ok": watchdog_ok,
        "elapsed_s": round(time.time() - t0, 1),
    }
    status, reasons = seal_decision(cold, no_rogue, watchdog_ok)
    rec = write_seal(signals, status, reasons)
    print("[B1-SEAL]", json.dumps(rec, ensure_ascii=False))
    if status == "SEALED":
        subprocess.run(["git", "-C", REPO, "tag", "-f", "L3-B1-sealed"], check=False)
        print("[B1-SEAL] MUHUR DUSTU (uc ampirik sinyal yesil) -> tag: L3-B1-sealed")
        return 0
    print("[B1-SEAL] MUHUR YOK -> kirmizi:", reasons)
    return 1


if __name__ == "__main__":
    raise SystemExit(run_live_seal())
