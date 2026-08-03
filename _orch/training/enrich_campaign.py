# -*- coding: utf-8 -*-
"""KASA profil egitimi — KONTROLLU cok-model konsensus kampanyasi (sifir-token).

Fable-sef orkestrasyonu: birden cok YEREL model ayni olay-sinyalini bagimsiz yorumlar; adaylar
birlestirilir (konsensus), Fable checklist'i (_orch/training/fable_checklist.md) + deterministik
gate (profile_enrich.gate: namespace allow-list + credential deny + provenance-gercek-sitelerden)
eler; survivors dry-run/apply. Provenance modelden ALINMAZ.

MAKINE SAGLIGI (kullanici direktifi 'kontrollu calis, bilgisayari yorma'):
  - Modeller SIRAYLA cagrilir (paralel agir cikarim YOK), aralarinda COOLDOWN.
  - Ollama kapaliysa nazikce cikar (thrash yok). Her cagri timeout + num_predict sinirli.
  - Gunluk tavan (MAX_APPLY) hem kalite hem DoS korumasi.

Kullanim:
  py _orch/training/enrich_campaign.py                # DRY-RUN (yazmaz)
  py _orch/training/enrich_campaign.py --apply        # gate'ten gecenleri yaz (tavanli)
  py _orch/training/enrich_campaign.py --models hermes3:8b,qwen2.5:7b --apply
"""
import sys; sys.path.insert(0, "d:/kasa")
import os, re, json, time, argparse, sqlite3, urllib.request
from datetime import datetime

from src.vault import cell_crypt
from src.vault.database import Vault
from src.mcp_server.tools import VaultTools
from src.distill import profile_enrich as pe   # build_signal, gate, ENRICH_PROMPT (tek dogruluk)

DB = "d:/kasa/kasa.db"
OLLAMA = "http://localhost:11434/api/generate"
PING = "http://localhost:11434/"
LOG_DIR = "d:/kasa/_orch/training/logs"

# Nazik varsayilanlar (makine sagligi).
DEFAULT_MODELS = ["hermes3:8b", "qwen2.5:7b"]
COOLDOWN_S = 15          # modeller arasi soguma (thermal nezaket)
CALL_TIMEOUT = 240       # tek model cagrisi
NUM_PREDICT = 1000
MAX_APPLY = 8            # gunluk tavan (fable_checklist)


def ollama_up() -> bool:
    try:
        with urllib.request.urlopen(PING, timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def call_one(model: str, signal: str):
    """Tek modelden aday fact listesi (+ ham yanit). Hata olursa ([], err)."""
    prompt = pe.ENRICH_PROMPT.format(signal=pe.sanitize_untrusted_text(signal))
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False,
                          "options": {"temperature": 0.15, "num_predict": NUM_PREDICT,
                                      "num_ctx": 8192}}).encode()
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=CALL_TIMEOUT) as r:
            raw = json.loads(r.read().decode("utf-8")).get("response", "")
    except Exception as e:
        return [], "ERR:%s" % e
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


def _norm_key(k: str) -> str:
    return re.sub(r"\s+", "", str(k)).strip(".").lower()


def merge_consensus(per_model: dict) -> list:
    """{model: [facts]} -> birlestirilmis aday listesi (konsensus + site union).
    Her oge: {key,value,sites,_consensus,_models}."""
    groups = {}
    for model, facts in per_model.items():
        for f in facts:
            if not isinstance(f, dict):
                continue
            key = f.get("key", "")
            nk = _norm_key(key)
            if not nk:
                continue
            g = groups.setdefault(nk, {"cands": [], "models": set(), "sites": set()})
            g["cands"].append((model, f))
            g["models"].add(model)
            for s in (f.get("sites") or []):
                g["sites"].add(s)
    merged = []
    for nk, g in groups.items():
        # En yuksek confidence'li adayi temsilci sec (esitlikte en uzun metin).
        def _score(mf):
            _, f = mf
            v = f.get("value") or {}
            conf = v.get("confidence", 0) if isinstance(v, dict) else 0
            txt = v.get("text", "") if isinstance(v, dict) else str(v)
            return (float(conf or 0), len(str(txt)))
        best_model, best = max(g["cands"], key=_score)
        merged.append({
            "key": best.get("key"),
            "value": best.get("value"),
            "sites": sorted(g["sites"]),
            "_consensus": len(g["models"]),
            "_models": sorted(g["models"]),
        })
    return merged


def fable_checklist(merged: list):
    """Fable checklist'in DETERMINISTIK uygulamasi (fable_checklist.md ile birebir).
    Doner (gecen, [(key,sebep)])."""
    passed, rejected = [], []
    for f in merged:
        key = str(f.get("key", ""))
        v = f.get("value") or {}
        text = (v.get("text", "") if isinstance(v, dict) else str(v)) or ""
        conf = float(v.get("confidence", 0) if isinstance(v, dict) else 0)
        cons = f.get("_consensus", 1)
        if key.count(".") < 2:
            rejected.append((key, "ozgul degil (key<3 parca)")); continue
        if len(text.strip()) < 12:
            rejected.append((key, "belirsiz metin (<12 char)")); continue
        if conf < 0.55:
            rejected.append((key, "dusuk guven (%.2f)" % conf)); continue
        if cons < 2 and conf < 0.7:
            rejected.append((key, "tek-model + guven<0.7")); continue
        passed.append(f)
    return passed, rejected


def existing_profile_keys():
    try:
        c = sqlite3.connect(DB).cursor()
        return {r[0] for r in c.execute("SELECT key FROM profile").fetchall()}
    except Exception:
        return set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--max-apply", type=int, default=MAX_APPLY)
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = open(os.path.join(LOG_DIR, "campaign_%s.log" % stamp), "w", encoding="utf-8")
    def out(msg):
        print(msg); log.write(msg + "\n"); log.flush()

    out("[campaign %s] models=%s apply=%s" % (stamp, models, args.apply))
    if not ollama_up():
        out("[SKIP] yerel model servisi kapali — nazikce cikildi (makine yorulmadi).")
        return 0

    key = cell_crypt.load_key(os.path.dirname(DB))
    conn = sqlite3.connect(DB); cur = conn.cursor()
    signal, dom_ids = pe.build_signal(cur, key)
    conn.close()
    out("[signal] %d domain agregelendi." % len(dom_ids))

    per_model = {}
    for i, model in enumerate(models):
        t0 = time.monotonic()
        facts, raw = call_one(model, signal)
        dt = time.monotonic() - t0
        out("[model %s] %d aday (%.0fs)" % (model, len(facts), dt))
        per_model[model] = facts
        if i < len(models) - 1:
            out("[cooldown] %ds (makine nezaketi)..." % COOLDOWN_S)
            time.sleep(COOLDOWN_S)

    merged = merge_consensus(per_model)
    out("[merge] %d benzersiz aday (konsensus)." % len(merged))
    passed, rej_cl = fable_checklist(merged)
    for k, why in rej_cl:
        out("   CHECKLIST-RED  %s  <- %s" % (k, why))
    # Deterministik gate (namespace + credential + provenance-gercek-sitelerden).
    survivors, rej_gate = pe.gate(passed, dom_ids)
    for k, why in rej_gate:
        out("   GATE-RED  %s  <- %s" % (k, why))

    # Mevcut ile ayni key+ayni metin tekrarini ele (gereksiz yazim).
    existing = existing_profile_keys()
    survivors = survivors[: args.max_apply]  # gunluk tavan
    out("[SURVIVORS] %d (tavan %d)" % (len(survivors), args.max_apply))
    for f in survivors:
        tag = "GUCLU" if any(m for m in merged if _norm_key(m["key"]) == _norm_key(f["key"]) and m["_consensus"] >= 2) else "tekil"
        out("   [%s] %s  ->  %s  (prov:%d)" % (tag, f["key"],
            json.dumps(f["value"], ensure_ascii=False)[:90], len(f["provenance_event_ids"])))

    # Artifact (audit + Fable/insan incelemesi icin).
    art = os.path.join(LOG_DIR, "candidates_%s.json" % stamp)
    json.dump({"survivors": survivors, "rejected_checklist": rej_cl, "rejected_gate": rej_gate,
               "models": models}, open(art, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    out("[artifact] %s" % art)

    if not args.apply:
        out("[DRY-RUN] hicbir sey yazilmadi. Commit: --apply")
        return 0

    vault = Vault(vault_path="d:/kasa"); vault.connect()
    tools = VaultTools(vault, agent_id="system")
    written = 0
    for f in survivors:
        try:
            tools.profile_write(f["key"], f["value"], f["provenance_event_ids"]); written += 1
        except Exception as e:
            out("   WRITE-FAIL %s: %s" % (f.get("key"), e))
    vault.close()
    out("[APPLY] %d fact yazildi (profile_write; audit+supersedes)." % written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
