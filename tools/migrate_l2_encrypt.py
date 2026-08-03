# -*- coding: utf-8 -*-
"""
L2 at-rest migration — mevcut kasa.db'deki DUZ METIN satirlari app-layer AES-GCM'e cevirir.

Sifrelenen: profile.value, events.content (AAD'li), audit.details (encrypt-then-hash + zincir
YENIDEN kurulur cunku eski entry_hash duz metin uzerinden hesaplanmisti).

GUVENLIK & GERI-DONUS:
  - Once kasa.db -> kasa.db.bak_<ts> kopyasi alinir (--no-backup ile kapatilabilir).
  - Idempotent: 'K1:' onekli hucre zaten sifreli -> atlanir (cift-sifreleme yok).
  - Migration sonrasi VERIFY: verify_chain()==True + ornek profile/event decrypt + K1: sayimi.
    Verify BASARISIZ ise .bak'tan OTOMATIK restore edilir ve hata dondurulur.
  - --dry-run: hicbir yazma yapmaz, yalniz ne yapilacaginin sayimini basar.

Kullanim:
  python tools/migrate_l2_encrypt.py --vault-path d:/kasa --dry-run
  python tools/migrate_l2_encrypt.py --vault-path d:/kasa
"""

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (1 ust dizin = depo koku). Sabit yol, depoyu klonlayan herkeste ve CI
# kosucusunda bu araci calismaz kilardi.
_KASA_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import sys
import os
import shutil
import time
import json
import hashlib
import argparse
import sqlite3

sys.path.insert(0, _KASA_ROOT)
from src.vault import cell_crypt


def _genesis() -> str:
    return hashlib.sha256(b"genesis").hexdigest()


def _audit_entry_hash(timestamp, agent_id, action, details_stored, previous_hash) -> str:
    h = hashlib.sha256()
    h.update(str(timestamp).encode("utf-8"))
    h.update(agent_id.encode("utf-8"))
    h.update(action.encode("utf-8"))
    h.update(details_stored.encode("utf-8"))
    h.update(previous_hash.encode("utf-8"))
    return h.hexdigest()


def migrate(vault_path: str, dry_run: bool = False):
    db_path = os.path.join(vault_path, "kasa.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    key = cell_crypt.load_key(vault_path)  # DPAPI-korumali _db_key

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # secure_delete: silinen/serbest birakilan icerik sifirlanir (UPDATE sonrasi eski plaintext kalmasin)
    conn.execute("PRAGMA secure_delete=ON")
    stats = {"profile_enc": 0, "profile_skip": 0, "events_enc": 0, "events_skip": 0,
             "audit_enc": 0, "audit_skip": 0}

    # profile.value (AAD = profile|value|key)
    for row in conn.execute("SELECT id, key, value FROM profile").fetchall():
        val = row["value"]
        if val is None:
            continue
        if cell_crypt.is_encrypted(val):
            stats["profile_skip"] += 1
            continue
        enc = cell_crypt.encrypt_cell(val, key, cell_crypt.aad_profile(row["key"]))
        if not dry_run:
            conn.execute("UPDATE profile SET value=? WHERE id=?", (enc, row["id"]))
        stats["profile_enc"] += 1

    # events.content (AAD = events|content)
    for row in conn.execute("SELECT id, content FROM events").fetchall():
        content = row["content"]
        if content is None:
            continue
        if cell_crypt.is_encrypted(content):
            stats["events_skip"] += 1
            continue
        enc = cell_crypt.encrypt_cell(content, key, cell_crypt.aad_event())
        if not dry_run:
            conn.execute("UPDATE events SET content=? WHERE id=?", (enc, row["id"]))
        stats["events_enc"] += 1

    # audit.details: encrypt-then-hash + zinciri YENIDEN kur (eski hash duz metin uzerindeydi).
    # Idempotent: zaten sifreli details icin ciphertext KORUNUR (yeniden sifrelenmez -> nonce sabit),
    # yalniz zincir hash'i deterministik olarak yeniden hesaplanir (ayni sonuc).
    last_hash = _genesis()
    for row in conn.execute(
        "SELECT id, timestamp, agent_id, action, details FROM audit ORDER BY id ASC"
    ).fetchall():
        details = row["details"] if row["details"] is not None else "{}"
        if cell_crypt.is_encrypted(details):
            details_stored = details
            stats["audit_skip"] += 1
        else:
            details_stored = cell_crypt.encrypt_cell(
                details, key, cell_crypt.aad_audit(row["agent_id"], row["action"], row["timestamp"]))
            stats["audit_enc"] += 1
        entry_hash = _audit_entry_hash(row["timestamp"], row["agent_id"], row["action"],
                                       details_stored, last_hash)
        if not dry_run:
            conn.execute("UPDATE audit SET details=?, previous_hash=?, entry_hash=? WHERE id=?",
                         (details_stored, last_hash, entry_hash, row["id"]))
        last_hash = entry_hash

    if not dry_run:
        conn.commit()
        # KRITIK: UPDATE eski plaintext'i serbest (free) sayfalarda birakabilir -> VACUUM DB'yi
        # yeniden yazip free sayfalari YOK eder (migration-kalinti sizintisi kapatilir).
        conn.execute("VACUUM")
        conn.commit()
    conn.close()
    return stats


def _verify(vault_path: str) -> tuple:
    """Migration sonrasi: verify_chain + ornek decrypt + K1: sayimi. (ok: bool, mesaj: str)"""
    from src.vault.database import Vault
    v = Vault(vault_path=vault_path)
    v.connect()
    try:
        if not v.audit_chain.verify_chain():
            return False, "verify_chain() False (zincir bozuk)"
        conn = v.get_connection()
        # ornek profile decrypt
        for row in conn.execute("SELECT key, value FROM profile LIMIT 5").fetchall():
            cell_crypt.decrypt_cell(row["value"], v._db_key, cell_crypt.aad_profile(row["key"]))
        for row in conn.execute("SELECT content FROM events WHERE content IS NOT NULL LIMIT 5").fetchall():
            cell_crypt.decrypt_cell(row["content"], v._db_key, cell_crypt.aad_event())
        # K1: sayimi
        enc_p = sum(1 for r in conn.execute("SELECT value FROM profile").fetchall()
                    if cell_crypt.is_encrypted(r["value"]))
        enc_e = sum(1 for r in conn.execute("SELECT content FROM events").fetchall()
                    if r["content"] and cell_crypt.is_encrypted(r["content"]))
        return True, f"verify_chain OK; ornek decrypt OK; sifreli profile={enc_p}, events={enc_e}"
    except Exception as e:
        return False, f"verify hata: {type(e).__name__}: {e}"
    finally:
        v.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault-path", default=_KASA_ROOT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    db_path = os.path.join(args.vault_path, "kasa.db")

    if args.dry_run:
        stats = migrate(args.vault_path, dry_run=True)
        print("[DRY-RUN] yazma YOK. Yapilacaklar:", json.dumps(stats))
        return 0

    # 1) .bak
    bak = None
    if not args.no_backup:
        bak = db_path + ".bak_" + time.strftime("%Y%m%d_%H%M%S")
        shutil.copy2(db_path, bak)
        print(f"[backup] {bak}")

    # 2) migrate
    stats = migrate(args.vault_path, dry_run=False)
    print("[migrate]", json.dumps(stats))

    # 3) verify -> basarisizsa OTOMATIK restore
    ok, msg = _verify(args.vault_path)
    if ok:
        print(f"[verify] OK — {msg}")
        print("[SONUC] MIGRATION BASARILI")
        return 0
    else:
        print(f"[verify] BASARISIZ — {msg}")
        if bak:
            shutil.copy2(bak, db_path)
            print(f"[restore] {bak} -> {db_path} (geri alindi)")
        print("[SONUC] MIGRATION GERI ALINDI")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
