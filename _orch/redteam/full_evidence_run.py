# -*- coding: utf-8 -*-
"""
TAM KANIT KOSUSU — her istek icin EKSIKSIZ veri: neden red oldu (hangi kapi) + red olurken
ne oldu (o istekte audit'e ne yazildi). Uydurma yok; her sey gercek HTTP + gercek audit'ten.

NE: izole sunucuya sirali + sürekli saldiri atar. Her istekte audit satir sayisini ISTEK-ONCESI
    ve SONRASI sayar; fark > 0 ise o istegin yazdirdigi satir(lar)i zincirden COZUP kaydeder.
    Boylece "red olurken ne oldu" tahmin degil, olcum olur.
NEDEN: red kodu (401/403/404/429/400/422) hangi KAPININ kapandigini, audit-etkisi ise sunucunun
    o an ne yaptigini gosterir. Ikisi birlikte tam tabloyu verir.
SINIR: izole vault; gercek veriye dokunulmaz. Hiz-siniri fazi 80 istek (kova kapasitesi 60'i
    asmak SART; 18-genel-tavani bu faz icin bilerek asilir — kanit amacli, izole sunucu).
"""
import json
import pathlib
import sqlite3
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from live_mcp_attack import start_isolated_server, _post, _exec_body, GREEN, RED, YELLOW, DIM, BOLD
from src.vault import cell_crypt


def classify_gate(code, detail):
    """HTTP kodu + detay mesajindan HANGI KAPININ kapandigini soyler."""
    d = (detail or "").lower()
    if code == 401:
        return "AUTH (token duvari)"
    if code == 403:
        if "mevcut değil" in d or "mevcut degil" in d:
            return "RESERVED (rezerve kimlik)"
        return "PERMISSION (deny-by-default)"
    if code == 404:
        return "NAMESPACE (allow-list disi)"
    if code == 429:
        return "RATE-LIMIT (token-bucket)"
    if code == 400:
        return "VALIDATION (deger/uzunluk)"
    if code == 422:
        return "VALIDATION (tip/parametre)"
    if code in (200, 201):
        return "IZIN VERILDI (savunma yok)"
    return f"DIGER ({code})"


def audit_count(db_path):
    conn = sqlite3.connect(db_path, timeout=5.0)
    try:
        return conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
    finally:
        conn.close()


def last_rows(db_path, key, n):
    """Son n audit satirini COZ (agent/action/result) — 'red olurken ne yazildi' kaniti."""
    if n <= 0:
        return []
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT agent_id, action, details, timestamp FROM audit "
                        "ORDER BY id DESC LIMIT ?", (n,)).fetchall()
    conn.close()
    out = []
    for r in reversed(rows):
        try:
            det = json.loads(cell_crypt.decrypt_cell(
                r["details"], key, cell_crypt.aad_audit(r["agent_id"], r["action"], r["timestamp"])))
            res = det.get("result") if isinstance(det, dict) else None
        except Exception:
            res = "(cozulemedi)"
        out.append({"agent_id": r["agent_id"], "action": r["action"], "result": res})
    return out


def build_requests(token):
    """Sirali + surekli saldiri istekleri. (faz, etiket, token_durumu, endpoint, body, satir_cek)."""
    reqs = []

    def add(phase, label, tok, endpoint, body, fetch=True):
        reqs.append({"phase": phase, "label": label, "token": tok,
                     "endpoint": endpoint, "body": body, "fetch": fetch})

    ep = "/v1/execute_tool"
    pr = lambda aid: _exec_body(aid, "profile_read", {"scope": "user.name"})

    # 1) Kimlik duvari
    add("1-AUTH", "token yok", "none", ep, pr("attacker"))
    add("1-AUTH", "yanlis token", "wrong", ep, pr("attacker"))
    # 2) Rezerve kimlik
    add("2-RESERVED", "system taklidi", "real", ep, pr("system"))
    # 3) Namespace
    add("3-NAMESPACE", "bilinmeyen arac", "real", ep, _exec_body("attacker", "read_secret_file", {}))
    add("3-NAMESPACE", "grant_permission (yetki yukseltme)", "real", ep,
        _exec_body("attacker", "grant_permission", {"scope": "admin:grant"}))
    # 4) Izin modeli (deny-by-default) — her arac ayri kapsam
    add("4-PERMISSION", "yetkisiz profile_read", "real", ep, pr("attacker"))
    add("4-PERMISSION", "yetkisiz profile_write", "real", ep,
        _exec_body("attacker", "profile_write", {"key": "user.name", "value": "PWNED", "provenance": []}))
    add("4-PERMISSION", "yetkisiz forget", "real", ep, _exec_body("attacker", "forget", {"topic": "user"}))
    add("4-PERMISSION", "yetkisiz audit_read", "real", ep, _exec_body("attacker", "audit_read", {}))
    add("4-PERMISSION", "yetkisiz prune", "real", ep, _exec_body("attacker", "prune_expired_events", {}))
    # 5) Girdi dogrulama (browser: events:write VAR -> dogrulama koduna ulasir)
    add("5-VALIDATION", "asiri uzun source (400)", "real", ep,
        _exec_body("browser", "event_ingest", {"source": "x" * 100, "type": "page",
                                               "content": {"text": "hi"}, "ttl_days": 30}))
    add("5-VALIDATION", "aralik disi ttl (400)", "real", ep,
        _exec_body("browser", "event_ingest", {"source": "s", "type": "page",
                                               "content": {"text": "hi"}, "ttl_days": 99999}))
    add("5-VALIDATION", "ttl string tip (422)", "real", ep,
        _exec_body("browser", "event_ingest", {"source": "s", "type": "page",
                                               "content": {"text": "hi"}, "ttl_days": "30"}))
    add("5-VALIDATION", "bilinmeyen parametre (422)", "real", ep,
        _exec_body("attacker", "profile_read", {"scope": "user.name", "evil": "x"}))
    add("5-VALIDATION", "eksik parametre (422)", "real", ep, _exec_body("attacker", "profile_read", {}))
    # 6) Ayricalikli kimlik taklidi (F-IMP) -> BREACH beklenir
    add("6-IMPERSONATE", "browser gibi event_ingest", "real", "/v1/ingest",
        {"agent_id": "browser", "tool": "event_ingest",
         "params": {"source": "adv", "type": "inject", "content": {"text": "attacker-was-here"}, "ttl_days": 5}})
    # 7) SUREKLI saldiri: ayni yetkisiz istegi tekrar tekrar (israr)
    for i in range(5):
        add("7-PERSIST", f"israrli yetkisiz okuma #{i+1}", "real", ep, pr(f"persist-{i}"))
    # 8) Hiz-siniri: SABIT kimlikle 80 istek (kapasite 60'i asar -> 429 gorunur). Satir cekme kapali (hizli).
    for i in range(80):
        add("8-RATELIMIT", f"sel #{i+1}", "real", ep, pr("flooder-fixed"), fetch=False)

    return reqs


def run():
    print(BOLD("\n=== TAM KANIT KOSUSU — gercek HTTP + gercek audit ===\n"))
    base, token, home, server, S = start_isolated_server()
    db = S.VAULT_INSTANCE.db_path
    key = S.VAULT_INSTANCE._db_key
    print(DIM(f"  izole sunucu : {base}"))
    print(DIM(f"  izole vault  : {home}  (gercek vault'a DOKUNULMADI)\n"))

    tokmap = {"real": token, "none": None, "wrong": "definitely-wrong-token"}
    reqs = build_requests(token)
    evidence = []
    log_path = HERE / "full_evidence_log.jsonl"

    cur_phase = None
    with open(log_path, "w", encoding="utf-8") as log:
        for i, rq in enumerate(reqs, 1):
            if rq["phase"] != cur_phase:
                cur_phase = rq["phase"]
                print(BOLD(f"\n--- FAZ {cur_phase} ---"))
            before = audit_count(db)
            code, body = _post(base, rq["endpoint"], tokmap[rq["token"]], rq["body"])
            after = audit_count(db)
            wrote = after - before
            # Detay mesajini cikar (JSON ise 'detail', degilse ham).
            try:
                detail = json.loads(body).get("detail", body)
            except Exception:
                detail = body
            gate = classify_gate(code, detail if isinstance(detail, str) else "")
            rows = last_rows(db, key, wrote) if (rq["fetch"] and wrote > 0) else []

            rec = {"seq": i, "phase": rq["phase"], "label": rq["label"], "endpoint": rq["endpoint"],
                   "token": rq["token"], "http_code": code,
                   "detail": (detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False))[:200],
                   "gate": gate, "audit_rows_written": wrote, "audit_written_rows": rows}
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            evidence.append(rec)

            # FAZ 8 (sel) satir satir basilmaz; ozet en sonda. Digerleri tam basilir.
            if rq["phase"] != "8-RATELIMIT":
                col = GREEN if code in (200, 201) else (YELLOW if code == 429 else DIM)
                auditinfo = (f"audit+{wrote}: " + ", ".join(f"{r['action']}={r['result']}" for r in rows)
                             if wrote > 0 else "audit-etkisi: YOK")
                print(f"  [{i:>3}] {rq['label']:<34s} HTTP {col(str(code))}  {DIM(gate)}")
                print(f"        detay: {DIM((rec['detail'])[:90])}")
                print(f"        {auditinfo}")

    # ---- FAZ 8 ozeti (gercek sayimlar) ----
    flood = [e for e in evidence if e["phase"] == "8-RATELIMIT"]
    codes = [e["http_code"] for e in flood]
    first429 = next((k + 1 for k, c in enumerate(codes) if c == 429), None)
    n403 = sum(1 for c in codes if c == 403)
    n429 = sum(1 for c in codes if c == 429)
    print(BOLD("\n--- FAZ 8-RATELIMIT (80 sel istegi) ---"))
    print(f"  ilk 429 kacinci istekte : {first429}")
    print(f"  403 (izin reddi) sayisi : {n403}")
    print(f"  429 (hiz-siniri) sayisi : {n429}")
    print(DIM("  -> ayni istek once IZIN'den (403), kova bosalinca HIZ-SINIRI'ndan (429) reddedildi."))

    # ---- TAM AUDIT DOKUMU (zincirden, cozulmus) ----
    print(BOLD("\n=== TAM AUDIT DOKUMU (izole zincirden, cozulmus) ==="))
    conn = sqlite3.connect(db, timeout=5.0)
    conn.row_factory = sqlite3.Row
    allrows = conn.execute("SELECT id, agent_id, action, details, timestamp FROM audit ORDER BY id ASC").fetchall()
    conn.close()
    by_result = {}
    by_action = {}
    for r in allrows:
        try:
            det = json.loads(cell_crypt.decrypt_cell(
                r["details"], key, cell_crypt.aad_audit(r["agent_id"], r["action"], r["timestamp"])))
            res = det.get("result", "(yok)") if isinstance(det, dict) else "(yok)"
        except Exception:
            res = "(cozulemedi)"
        by_result[res] = by_result.get(res, 0) + 1
        by_action[r["action"]] = by_action.get(r["action"], 0) + 1
    print(f"  toplam audit satiri : {len(allrows)}")
    print(f"  action dagilimi     : {by_action}")
    print(f"  result dagilimi     : {by_result}")

    # ---- ZINCIR DOGRULAMA ----
    from src.vault.audit import AuditChain
    conn2 = sqlite3.connect(db, timeout=5.0)
    conn2.row_factory = sqlite3.Row
    chain_ok = bool(AuditChain(conn2).verify_chain())
    conn2.close()

    # ---- SAYIMLAR / KAPI DAGILIMI ----
    non_flood = [e for e in evidence if e["phase"] != "8-RATELIMIT"]
    gate_dist = {}
    for e in non_flood:
        gate_dist[e["gate"]] = gate_dist.get(e["gate"], 0) + 1
    wrote_yes = sum(1 for e in non_flood if e["audit_rows_written"] > 0)
    print(BOLD("\n=== SAYIMLAR (faz 1-7, sel haric) ==="))
    print(f"  toplam istek        : {len(non_flood)}")
    print(f"  kapi dagilimi       : {gate_dist}")
    print(f"  audit izi BIRAKAN   : {wrote_yes}/{len(non_flood)}")
    print(f"  audit zinciri       : " + (GREEN("SAGLAM") if chain_ok else RED("BOZUK")))
    print(DIM(f"\n  tam kayit (her istek): {log_path}\n"))

    # arsiv
    import shutil
    logs_dir = HERE / "logs"
    logs_dir.mkdir(exist_ok=True)
    shutil.copy(log_path, logs_dir / ("full_evidence_" + time.strftime("%Y%m%d_%H%M%S") + ".jsonl"))

    try:
        server.should_exit = True
    except Exception:
        pass
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
