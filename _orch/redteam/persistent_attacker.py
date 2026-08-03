# -*- coding: utf-8 -*-
"""
KASA 'saldiran site' — ISRARCI, uyarlanan SENARYO saldirgani (kendi gunlugu ile).

NE: live_mcp_attack.py'nin IZOLE sunucusunu kullanir; ama tek-atislik test yerine, bir
    HEDEFI olan ve engellendikce TAKTIK DEGISTIREN israrci bir saldirgan canlandirir.
    Saldirgan KENDI gunlugunu tutar (attacker_journal.jsonl) — savunucunun audit'inden AYRI.
NEDEN: (1) Gercek dusman tek deneme yapmaz; reddedilince yeniden dener, kimlik degistirir,
    ayricalikli kimligi taklit eder, yetki yukseltmeye calisir.
    (2) Iki AYRI gunluk (saldirgan-gorusu vs savunucu-kaydi) UZLASTIRILINCA telemetri
    boslugu OLCUYE gelir: saldirgan X deneme dedi, audit Y kaydetti -> fark = gorunmezlik
    (orn. C2 sessiz-ret bulgusu artik somut bir UYUSMAZLIK olarak cikar).

SINIR (dürüst, bir AI modeli olarak): bu bir SENARYO. Kendi makinen, izole vault, YETKILI
    test. Israr SINIRLIDIR (tur/istek tavani var) — DoS silahi degil, dusman-emülasyonu.
    Zararli icerik uretmez; yalnizca KASA'nin kendi yetki/kimlik sinirlarini yoklar.

Tum HTTP trafigi GERCEK loopback uzerinden gider (http://127.0.0.1:<port>) — in-process
    fonksiyon cagrisi degil. Yalniz saldiri-sonrasi UZLASTIRMA in-process okur (taze baglanti).
"""
import json
import pathlib
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

# Izole sunucu + HTTP yardimcilari + renkleri saldiri aracindan yeniden kullan (DRY).
from live_mcp_attack import (start_isolated_server, _post, _exec_body, MAX_ATTEMPTS,
                             GREEN, RED, YELLOW, DIM, BOLD)


class Journal:
    """Saldirganin KENDI gunlugu — savunucunun audit'inden bagimsiz, saldirgan gozuyle."""

    def __init__(self, path):
        self.path = path
        self._f = open(path, "w", encoding="utf-8")
        self._n = 0

    def write(self, **rec):
        self._f.write(json.dumps({"seq": self._n, "t": round(time.monotonic(), 3), **rec},
                                 ensure_ascii=False) + "\n")
        self._f.flush()
        self._n += 1

    def close(self):
        self._f.close()


def _classify(code):
    """HTTP kodunu saldirgan-diline cevir: (makine-etiketi, renkli-insan-etiketi)."""
    if code in (200, 201):
        return "breach", RED("ELE GECIRDI")
    if code == 401:
        return "blocked-auth", GREEN("engellendi (kimlik)")
    if code == 403:
        return "blocked-perm", GREEN("engellendi (izin)")
    if code == 404:
        return "blocked-namespace", GREEN("engellendi (namespace)")
    if code == 429:
        return "rate-limited", YELLOW("hiz-siniri")
    return "other", YELLOW("HTTP %s" % code)


def pursue(base, token, j, goal, tactics):
    """Bir hedefi ISRARLA kovala: taktikleri sirayla dene, ilk BREACH'te dur; yoksa pes et.
    Her deneme saldirgan gunlugune yazilir (savunucunun ne kaydettiginden BAGIMSIZ)."""
    print(BOLD("HEDEF: " + goal))
    breached = False
    for tactic, aid, tool, params in tactics:
        code, body = _post(base, "/v1/execute_tool", token, _exec_body(aid, tool, params))
        verdict, human = _classify(code)
        print(f"    - {tactic:<34s} [{aid:>8s}] {tool:<18s} -> {human}  {DIM('HTTP %s' % code)}")
        j.write(goal=goal, tactic=tactic, agent_id=aid, tool=tool, params=params,
                http=code, verdict=verdict, body=body[:160])
        if code in (200, 201):
            print("      " + RED(">> ELE GECIRDI: hedef delindi!"))
            breached = True
            break
    if breached:
        print()
    else:
        print("      " + GREEN(">> PES ETTI: duvar tuttu, hedef delinemedi.\n"))
    return breached


def dos_flood(base, token, j, n, capacity):
    """Freni yor: DONEN kimlikle sel (A6). Ayricalik kazandirmaz ama hiz-sinirini asar.
    DURUST GUARD: n kova kapasitesini asmadikca sabit kimlik de 429 almazdi -> 0x429 'baypas'
    DEGIL, sadece esik-alti. O yuzden n<=capacity ise KESIN DEGIL raporla (sahte 'asildi' yok)."""
    print(BOLD("HEDEF: FRENI YOR (donen kimlikle sel — A6)"))
    got429 = 0
    for i in range(n):
        code, _ = _post(base, "/v1/execute_tool", token,
                        _exec_body(f"dos-{i}", "profile_read", {"scope": "user.name"}))
        if code == 429:
            got429 += 1
    conclusive = n > capacity
    verdict = ("inconclusive" if not conclusive else ("bypassed" if got429 == 0 else "throttled"))
    j.write(goal="rate-limit DoS", tactic="rotate-flood", requests=n, capacity=capacity,
            http_429=got429, conclusive=conclusive, verdict=verdict)
    if not conclusive:
        print("      " + YELLOW(f">> KESIN DEGIL: {n} <= kova kapasitesi ({capacity}); bu "
                                f"hacimde fren zaten devreye girmez. Baypas icin n>{capacity} gerek.\n"))
    elif got429 == 0:
        print("      " + RED(f">> FREN ASILDI: {n}/{n} istek gecti, 0 x 429 (A6 canli).\n"))
    else:
        print("      " + GREEN(f">> FREN TUTTU: {got429} x 429.\n"))


def reconcile(S, jpath):
    """UZLASTIRMA: saldirgan KAC deneme yaptigini iddia ediyor, savunucu KAC tanesini kaydetti?
    Fark = gorunmezlik. audit_read/prune reddi kaydedilmedigi icin burada UYUSMAZLIK cikar
    (C2 sessiz-ret bulgusu artik somut). Breach kaydedildiyse: yetki delindi AMA adli iz VAR."""
    import sqlite3
    print(BOLD("=== UZLASTIRMA: saldirgan-gorusu  vs  savunucu-kaydi ==="))
    KASA_TOOLS = {"profile_read", "profile_write", "forget", "audit_read",
                  "prune_expired_events", "event_ingest"}

    # Saldirgan gorusu: KASA aracina yapilan deneme sayisi (araç bazinda).
    atk = {}
    with open(jpath, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            t = r.get("tool")
            if t in KASA_TOOLS:
                atk[t] = atk.get(t, 0) + 1

    # Savunucu gorusu: audit tablosunda action bazinda kayit sayisi (taze salt-okuyan baglanti).
    conn = sqlite3.connect(S.VAULT_INSTANCE.db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    dfn = {}
    for row in conn.execute("SELECT action FROM audit").fetchall():
        dfn[row["action"]] = dfn.get(row["action"], 0) + 1
    conn.close()

    print(f"    {'ACTION':<22s}{'saldirgan':>11s}{'audit-kayit':>13s}   DURUM")
    mismatches = []
    for a in sorted(set(atk) | set(KASA_TOOLS)):
        av, dv = atk.get(a, 0), dfn.get(a, 0)
        if av == 0:
            continue
        if dv == 0:
            status = RED("UYUSMAZLIK: denendi ama audit BOS (sessiz ret)")
            mismatches.append(a)
        else:
            status = GREEN("kayitli (adli iz var)")
        print(f"    {a:<22s}{av:>11d}{dv:>13d}   {status}")
    print()
    if mismatches:
        print("    " + YELLOW("Gorunmez kalan (savunucu kaydetmedi): " + ", ".join(mismatches)))
        print("    " + DIM("-> C2 sessiz-ret bulgusu, saldirgan-vs-savunucu uyusmazligi olarak dogrulandi.\n"))
    return mismatches


def run():
    print(BOLD("\n=== KASA 'SALDIRAN SITE' — israrci senaryo saldirgani ===\n"))
    base, token, home, server, S = start_isolated_server()
    print(DIM(f"  hedef (izole): {base}"))
    print(DIM(f"  izole vault  : {home}"))
    print(DIM("  (kullanicinin gercek vault'una DOKUNULMADI; yetkili senaryo testi)\n"))

    jpath = HERE / "attacker_journal.jsonl"
    j = Journal(jpath)

    # HEDEF 1 — sahibin profilini sizdir (okuma yetkisi yok; her taktik denenir)
    pursue(base, token, j, "Sahibin profilini SIZDIR (user.*)", [
        ("dogrudan istek", "adv", "profile_read", {"scope": "user.*"}),
        ("ISRAR: ayni istegi tekrarla", "adv", "profile_read", {"scope": "user.*"}),
        ("kimlik degistir (rotate)", "adv-2", "profile_read", {"scope": "user.*"}),
        ("sistem gibi davran", "system", "profile_read", {"scope": "user.*"}),
        ("kendine yetki ver", "adv", "grant_permission", {"scope": "profile:read:user.*"}),
        ("kapsami genislet (joker)", "adv-3", "profile_read", {"scope": "*"}),
    ])

    # HEDEF 2 — sahibin hafizasini sil (admin:forget yok)
    pursue(base, token, j, "Sahibin HAFIZASINI SIL (forget)", [
        ("dogrudan forget", "adv", "forget", {"topic": "user"}),
        ("ISRAR: tekrar dene", "adv", "forget", {"topic": "user"}),
        ("kimlik degistir", "adv-4", "forget", {"topic": "user"}),
        ("kendine admin:forget ver", "adv", "grant_permission", {"scope": "admin:forget"}),
    ])

    # HEDEF 3 — denetim gunlugunu oku (audit_read reddi KAYDEDILMIYOR -> sessiz-ret tetigi)
    pursue(base, token, j, "Denetim gunlugunu OKU (audit_read)", [
        ("dogrudan audit_read", "adv", "audit_read", {}),
        ("ISRAR: baska kimlik", "adv-5", "audit_read", {}),
    ])

    # HEDEF 4 — AYRICALIKLI KIMLIGI TAKLIT ET: 'browser' events:write iznine sahip.
    # agent_id istemci-beyanli oldugu icin token'i olan saldirgan 'browser' gibi yazabilir.
    pursue(base, token, j, "Ayricalikli kimligi TAKLIT ET ('browser' gibi yaz)", [
        ("browser gibi olay yaz", "browser", "event_ingest",
         {"source": "adv", "type": "inject",
          "content": {"text": "attacker-was-here"}, "ttl_days": 5}),
    ])

    # HEDEF 5 — freni yor (donen kimlikle sel; GUVENLI ISRAR TAVANI = MAX_ATTEMPTS)
    dos_flood(base, token, j, n=MAX_ATTEMPTS, capacity=S.RATE_LIMITER.capacity)

    j.close()

    # ---- LOG ARSIVI: her kosu zaman-damgali saklanir (sahip istegi: sureci kaydet) ----
    import shutil
    logs_dir = HERE / "logs"
    logs_dir.mkdir(exist_ok=True)
    archived = logs_dir / ("attacker_journal_" + time.strftime("%Y%m%d_%H%M%S") + ".jsonl")
    shutil.copy(jpath, archived)
    print(DIM(f"  saldirgan gunlugu: {jpath}"))
    print(DIM(f"  arsiv           : {archived}\n"))
    mismatches = reconcile(S, jpath)

    try:
        server.should_exit = True
    except Exception:
        pass
    return 0 if not mismatches else 2  # 2 = telemetri boslugu (gorunmez ret) bulundu


if __name__ == "__main__":
    raise SystemExit(run())
