# -*- coding: utf-8 -*-
"""RED-TEAM GOZLEMCI (observer, Faz-1 pasif): lokal-model saldiri korpusunu IZOLE bir KASA MCP
sunucusuna atesler, savunmayi GOZLER + deterministik verdict cikarir. KASA'nin GERCEK savunma
kodu calisir; yalniz VERI izole temp-vault'ta (gercek 77-event vault zehirlenmez).

Karar (yargic) deterministik; ben (gozlemci) tespit yaparim. Faz-2 (aktif mudahale) ayri.
Kullanim: python _orch/redteam/observe_run.py <corpus.json>
"""
import glob
import importlib
import json
import os
import sys
import tempfile

sys.path.insert(0, "d:/kasa")


def start_isolated_server():
    """KASA_VAULT_PATH -> temp; server reload -> VAULT_INSTANCE temp'e baglanir (izole)."""
    tmp = tempfile.mkdtemp(prefix="kasa_redteam_")
    os.environ["KASA_VAULT_PATH"] = tmp
    srv = importlib.import_module("src.mcp_server.server")
    importlib.reload(srv)
    return srv, tmp


def _db_has_plaintext(vault_dir, needle):
    """Temp vault'un ham db baytlarinda needle (poison duz metni) var mi? -> at-rest sizinti kaniti."""
    if not needle:
        return None
    hits = []
    for db in glob.glob(os.path.join(vault_dir, "**", "*.db"), recursive=True) + \
             glob.glob(os.path.join(vault_dir, "**", "*.db-wal"), recursive=True):
        try:
            with open(db, "rb") as f:
                if needle.encode("utf-8", "ignore") in f.read():
                    hits.append(os.path.basename(db))
        except OSError:
            pass
    return hits


def _needle_from(scn):
    """Poison senaryosundan ayirt edici duz-metin parcasi (at-rest taramasi icin)."""
    p = scn.get("parameters", {}) or {}
    for k in ("value", "content", "topic", "description"):
        v = p.get(k)
        if isinstance(v, str) and len(v) >= 8:
            return v[:40]
        if isinstance(v, dict):
            s = json.dumps(v, ensure_ascii=False)
            if len(s) >= 8:
                return s[:40]
    return None


def verdict(scn, status, body):
    exp = (scn.get("expected_defense") or "").lower()
    cat = (scn.get("category") or "").lower()
    low = body.lower()
    if "401" in exp or cat == "auth_bypass":
        return "DEFENDED" if status == 401 else "BREACH?"
    if "403" in exp or "reserved" in exp or cat == "authz_impersonation":
        return "DEFENDED" if status == 403 else "BREACH?"
    if cat in ("privilege_escalation", "tool_allowlist_bypass") or "permission" in exp:
        blocked = status >= 400 or any(w in low for w in ("permission", "denied", "error", "yok", "izin"))
        return "DEFENDED" if blocked else "BREACH?"
    return "OBSERVE"  # poison/exfil: atrest taramasiyla ayrica degerlendirilir


def run(corpus_path):
    corpus = json.load(open(corpus_path, encoding="utf-8"))
    srv, vault_dir = start_isolated_server()
    from fastapi.testclient import TestClient

    findings = []
    with TestClient(srv.app, raise_server_exceptions=False) as client:
        good = {"Authorization": f"Bearer {srv._BEARER_TOKEN}"}
        bad = {"Authorization": "Bearer wrong-token-attacker"}
        for scn in corpus:
            cat = (scn.get("category") or "").lower()
            headers = bad if cat == "auth_bypass" else good
            body = {
                "tool_calls": [{"tool_name": scn.get("tool_name"),
                                "parameters": scn.get("parameters", {}) or {}}],
                "agent_id": scn.get("agent_id", "attacker"),
            }
            try:
                r = client.post("/v1/execute_tool", json=body, headers=headers)
                status, text = r.status_code, r.text[:400]
            except Exception as e:
                status, text = -1, f"EXC:{e}"

            v = verdict(scn, status, text)
            # poison/exfil: at-rest sizinti taramasi (verdict'i somutlastirir)
            atrest = None
            if v == "OBSERVE":
                needle = _needle_from(scn)
                hits = _db_has_plaintext(vault_dir, needle) if status < 400 else []
                if status < 400:
                    atrest = "PLAINTEXT-LEAK:" + ",".join(hits) if hits else "encrypted/absent"
                    v = "BREACH?" if hits else "DEFENDED"
                else:
                    v = "DEFENDED"  # yazma reddedildi
            findings.append({"id": scn.get("id"), "cat": cat, "tool": scn.get("tool_name"),
                             "agent": scn.get("agent_id"), "status": status, "verdict": v,
                             "atrest": atrest, "resp": text[:120]})

    # Rapor
    print("=" * 92)
    print(f"RED-TEAM FAZ-1 (PASIF GOZLEM) — {len(findings)} senaryo | izole vault: {vault_dir}")
    print("=" * 92)
    breaches = 0
    for f in findings:
        flag = "!!" if f["verdict"] == "BREACH?" else "  "
        if f["verdict"] == "BREACH?":
            breaches += 1
        print(f"{flag} [{f['verdict']:9}] {str(f['id'])[:16]:16} {f['cat'][:20]:20} "
              f"tool={str(f['tool'])[:16]:16} agent={str(f['agent'])[:12]:12} http={f['status']}")
        if f["atrest"]:
            print(f"       at-rest: {f['atrest']}")
        if f["verdict"] == "BREACH?":
            print(f"       resp: {f['resp']}")
    print("-" * 92)
    print(f"OZET: {len(findings)} senaryo, {breaches} olasi ihlal (BREACH?), "
          f"{len(findings)-breaches} savunuldu. Yargic=deterministik; tespit=gozlemci.")
    json.dump(findings, open(os.path.join(os.path.dirname(corpus_path), "observe_findings.json"),
                             "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "attack_corpus.json")
