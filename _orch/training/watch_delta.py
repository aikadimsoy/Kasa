# -*- coding: utf-8 -*-
"""KASA egitim delta-gozcusu — 15-gun otonom, MAKINE-NAZIK.

Gunde bir kez calisir (zamanlanmis gorev). Yeni olay GELDIYSE (>= MIN_NEW) enrichment
kampanyasini delta uzerinde calistirir; GELMEDIYSE hicbir sey yapmaz (sifira-yakin yuk).
Boylece statik veride bosuna GPU dovulmez; sadece gercek yeni veri egitimi tetikler.

Guvenlik: her apply oncesi DB yedegi (rollback); deterministik checklist+gate (enrich_campaign);
sabit gunluk tavan; ollama kapaliysa nazikce cikar. Fable yokken 'sef kalitesi' = checklist+gate
(fable_checklist.md deterministik uygulanir) — son soz her zaman kuralda.
"""
import sys; sys.path.insert(0, "d:/kasa")
import os, json, time, sqlite3, shutil, subprocess, urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DB = "d:/kasa/kasa.db"
STATE = os.path.join(HERE, "state.json")
LOG = os.path.join(HERE, "logs")
BAK = "d:/kasa/_bak_archive"
PING = "http://localhost:11434/"

MIN_NEW = 5              # bu kadar yeni olay olmadan egitim tetiklenmez (gurultu/DoS onleme)
MODELS = "hermes3:8b,qwen2.5:7b"
MAX_APPLY = 6            # gunluk tavan
HARD_TIMEOUT = 900       # kampanya en fazla 15 dk (makine guvenligi)


def log(msg):
    os.makedirs(LOG, exist_ok=True)
    line = "%s  %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line)
    with open(os.path.join(LOG, "watch.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def event_count():
    try:
        return sqlite3.connect(DB).cursor().execute("SELECT COUNT(*) FROM events").fetchone()[0]
    except Exception as e:
        log("DB okunamadi: %s" % e); return None


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def save_state(d):
    json.dump(d, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def ollama_up():
    try:
        with urllib.request.urlopen(PING, timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    cur = event_count()
    if cur is None:
        return 0
    st = load_state()
    last = st.get("last_event_count")
    if last is None:
        # Ilk calisma: mevcut sayiyi tohumla, egitim TETIKLEME (ilk kampanya elle yapildi).
        save_state({"last_event_count": cur, "last_run": datetime.now().isoformat(), "note": "seeded"})
        log("SEED last_event_count=%d (ilk gozcu; egitim tetiklenmedi)." % cur)
        return 0

    delta = cur - last
    if delta < MIN_NEW:
        log("IDLE  events=%d delta=%d (<%d) — bosta, makine yorulmadi." % (cur, delta, MIN_NEW))
        save_state({**st, "last_run": datetime.now().isoformat(), "last_event_count": cur})
        return 0

    if not ollama_up():
        log("SKIP  delta=%d ama yerel model servisi kapali — sonraki tura ertelendi." % delta)
        return 0

    # Yeni veri var + servis acik -> yedek al, kampanya calistir (deterministik checklist+gate).
    os.makedirs(BAK, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        shutil.copy2(DB, os.path.join(BAK, "kasa_watch_%s.db" % stamp))
    except Exception as e:
        log("YEDEK-FAIL %s — guvenlik icin egitim iptal." % e); return 0

    log("TRAIN delta=%d — kampanya baslatiliyor (yedek alindi)." % delta)
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "enrich_campaign.py"),
             "--apply", "--models", MODELS, "--max-apply", str(MAX_APPLY)],
            timeout=HARD_TIMEOUT, capture_output=True, text=True)
        tail = "\n".join((r.stdout or "").splitlines()[-4:])
        log("TRAIN bitti (exit %d). %s" % (r.returncode, tail.replace("\n", " | ")))
    except subprocess.TimeoutExpired:
        log("TRAIN timeout (%ds) — durduruldu (makine korumasi)." % HARD_TIMEOUT)

    save_state({"last_event_count": event_count(), "last_run": datetime.now().isoformat()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
