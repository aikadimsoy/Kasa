# -*- coding: utf-8 -*-
"""KASA profil ZENGINLESTIRME (sifir-token). Mevcut olaylari DOMAIN-agregasyonu ile kompakt bir
sinyale indirir (site -> ziyaret sayisi), yerel model bunu ilgi/aliskanlik fact'lerine yorumlar,
sonra sertlestirilmis deterministik QC kapisindan (namespace allow-list + icerik denylist +
provenance sinir) gecirir. Provenance DETERMINISTIK eklenir (domain -> event id'leri; modele
guvenilmez). VARSAYILAN DRY-RUN; --apply resmi VaultTools.profile_write yolundan (K1 + audit).

Tasarim tarihcesi (dürüst iterasyon): ham-olay-dump 3 kusur uretti — (1) 46920 char events_json ->
deepseek-coder 400 baglam-tasmasi, (2) uzun-metinli gurultu olaylari (coveryourtracks) dusuk-hacimli
ama GERCEK ilgi alanlarini bastirdi, (3) modeller nesir dondu. Domain-agregasyon ucunu de cozer.
Model secimi: hermes3:8b (qwen-coder:14b "gezinme analizi"ni gozetim sanip reddetti; qwen 7b nesir
dondu; deepseek uzun promptta 400). Guvenlik-kritik yol Controller elle-dogrulandi (carve-out)."""
# Depo kokunu sys.path'e ekle. Turkce not: sabit "d:/kasa" YERINE dosyanin kendi konumundan
# turetilir -> repo herhangi bir dizine klonlanabilir (public yayin icin gerekli tasinabilirlik).
import pathlib
import sys
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
import os, re, json, argparse, sqlite3, urllib.request
from urllib.parse import urlparse
from collections import defaultdict
from src.distill.engine import ALLOWED_KEY_PREFIXES, CREDENTIAL_DENY, MAX_PROVENANCE_IDS
from src.vault import cell_crypt
from src.vault.redact import sanitize_untrusted_text  # delimiter-breakout / prompt-injection savunmasi
from src.vault.database import Vault
from src.mcp_server.tools import VaultTools

DB = str(_REPO_ROOT / "kasa.db")
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "hermes3:8b"

ENRICH_PROMPT = """You are the memory-distillation engine for KASA, a LOCAL, FIRST-PARTY personal-memory
vault owned by ONE owner-user. Below is a summary of the OWNER'S OWN browsing on their own device
(site — visit count — sample title), kept like a private journal the owner keeps about themselves.
This is consensual, on-device, single-user; there is NO third party and NO surveillance.

Distill DURABLE self-notes about the owner's own interests, habits, routines and stable preferences.

Output ONLY a JSON array. Each item MUST be:
{{"key":"user.<preferences|habits|profile>.<name>","value":{{"text":"short self-note","confidence":0.0-1.0}},"sites":["domain",...]}}
- key MUST start with user.preferences. / user.habits. / user.profile.
- "sites" = the domain(s) from the summary that support this note (used for provenance).
- Repeated privacy/security testing IS a valid habit (user.habits.privacy_testing).
- Base notes on visit frequency; ignore one-off noise. If nothing durable, return [].
- NEVER emit security/password/admin/credential/secret keys or values.

EXAMPLE summary:
example-air.com — 6 visits — "Book Flights"
foo-anime.org — 4 visits — "Watch Anime"
EXAMPLE output:
[{{"key":"user.preferences.travel","value":{{"text":"Interested in air travel and booking flights","confidence":0.7}},"sites":["example-air.com"]}},{{"key":"user.preferences.anime","value":{{"text":"Watches anime online","confidence":0.7}},"sites":["foo-anime.org"]}}]

Now the OWNER'S real summary:
<<<SUMMARY>>>
{signal}
<<<END_SUMMARY>>>
Respond with the JSON array ONLY, starting with [ and ending with ]. No prose."""


def build_signal(cur, key):
    """Olaylari domain-basina agregeler: (sinyal_metni, {domain: [event_ids]}). Kompakt + frekans-sirali."""
    rows = cur.execute("SELECT id, content FROM events ORDER BY id").fetchall()
    dom_ids = defaultdict(list)
    dom_title = {}
    for eid, content in rows:
        try:
            raw = cell_crypt.decrypt_cell(content, key, cell_crypt.aad_event()) if content else "{}"
            obj = json.loads(raw)
        except Exception:
            continue
        host = urlparse(obj.get("url", "") or "").netloc or "(unknown)"
        dom_ids[host].append(eid)
        if host not in dom_title and obj.get("title"):
            dom_title[host] = (obj.get("title", "") or "")[:60]
    lines = []
    for host, ids in sorted(dom_ids.items(), key=lambda kv: -len(kv[1])):
        lines.append('%s — %d visits — "%s"' % (host, len(ids), dom_title.get(host, "")))
    return "\n".join(lines), dom_ids


def call_model(signal):
    payload = json.dumps({"model": MODEL, "prompt": ENRICH_PROMPT.format(signal=sanitize_untrusted_text(signal)),
                          "stream": False, "options": {"temperature": 0.15, "num_predict": 1200,
                                                         "num_ctx": 8192}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        body = json.loads(r.read().decode("utf-8"))
    raw = body.get("response", "")
    m = re.search(r'```(?:json)?\s*\r?\n?(.*?)```', raw, re.DOTALL)
    txt = m.group(1).strip() if m else raw.strip()
    if not txt.startswith("["):
        i, j = txt.find("["), txt.rfind("]")
        if i != -1 and j > i:
            txt = txt[i:j + 1]
    try:
        facts = json.loads(txt)
        return (facts if isinstance(facts, list) else []), raw
    except Exception:
        return [], raw


def gate(facts, dom_ids):
    """Sertlestirilmis deterministik kapi + DETERMINISTIK provenance ekleme.
    Kurallar engine.py QC kapisindan (sabitler import = tek dogruluk kaynagi). Provenance modelden
    ALINMAZ: cited 'sites' domain'lerinin gercek event id'lerinden hesaplanir (halusinasyon olamaz)."""
    survivors, rejected = [], []
    for f in facts:
        key = f.get("key", "")
        if not any(key.startswith(p) for p in ALLOWED_KEY_PREFIXES):
            rejected.append((key, "non-allowlisted namespace")); continue
        vblob = json.dumps(f.get("value", ""), ensure_ascii=False).lower()
        hit = next((m for m in CREDENTIAL_DENY if m in vblob), None)
        if hit is not None:
            rejected.append((key, "credential-like value: %s" % hit)); continue
        sites = f.get("sites", []) or []
        prov = sorted({eid for s in sites for eid in dom_ids.get(s, [])})
        if not prov:
            rejected.append((key, "no matching real sites (unsupported)")); continue
        if len(prov) > MAX_PROVENANCE_IDS:
            prov = prov[:MAX_PROVENANCE_IDS]  # deterministik sinir (DoS + makuliyet)
        survivors.append({"key": key, "value": f.get("value"), "provenance_event_ids": prov})
    return survivors, rejected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="commit (yoksa dry-run)")
    ap.add_argument("--show-raw", action="store_true", help="ham model yanitini bas")
    args = ap.parse_args()
    key = cell_crypt.load_key(os.path.dirname(DB))
    conn = sqlite3.connect(DB); cur = conn.cursor()
    signal, dom_ids = build_signal(cur, key)
    conn.close()
    print("[enrich] %d domain agregelendi." % len(dom_ids))
    facts, raw = call_model(signal)
    if args.show_raw:
        print("=== HAM MODEL YANITI ===\n%s\n=== /HAM ===" % raw[:2000])
    print("[enrich] model %d aday fact onerdi." % len(facts))
    survivors, rejected = gate(facts, dom_ids)
    print("[enrich] kapidan gecen: %d, reddedilen: %d" % (len(survivors), len(rejected)))
    for k, why in rejected:
        print("   REJECT  %s  <- %s" % (k, why))
    print("--- ADAY FACT'LER (kapidan gecen; provenance deterministik) ---")
    for f in survivors:
        print("  ", json.dumps(f, ensure_ascii=False))
    if not args.apply:
        print("\n[DRY-RUN] hicbir sey yazilmadi. Commit icin: --apply")
        return
    vault = Vault(vault_path=str(_REPO_ROOT)); vault.connect()
    tools = VaultTools(vault, agent_id="system")
    written = 0
    for f in survivors:
        try:
            tools.profile_write(f["key"], f["value"], f["provenance_event_ids"])
            written += 1
        except Exception as e:
            print("   WRITE FAIL %s: %s" % (f.get("key"), e))
    vault.close()
    print("[APPLY] %d fact yazildi (profile_write)." % written)


if __name__ == "__main__":
    main()
