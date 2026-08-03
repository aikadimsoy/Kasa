# kasa/src/dashboard/stats.py

"""
Read-only dashboard aggregator — the UI security boundary (read-through-redact).

Turkce not: Bu modul panoya YALNIZ aggregate + maskeli yapisal veri dondurur. Ham
(desifre edilmis) hucre icerigi response'a HIC girmez. Salt-okunur: hicbir yazma /
mutation / audit kaydi yok.

Olculebilirlik gercegi: icerik ingest'te ZATEN maskeleniyor (tools.event_ingest ve
profile_write -> redact.scan) ve at-rest sifreleniyor. Dolayisiyla saklanan veriyi
tekrar taramak orijinal sirlari geri getirmez (idempotent redact). Bu yuzden iki DURUST
metrik olcuyoruz:
  - masked_markers   : saklanan icerikteki '[REDACTED]' isaretci sayisi = maskelenmis sir.
  - live_secrets_found: saklanan icerigi YENIDEN tarayinca cikan (henuz maskelenmemis) sir.
    Kapidan gecmis veri icin 0 OLMALI; >0 ise legacy plaintext satiri var demektir (uyari).

by_type gecmis dagilimi persist EDILMEDIGI icin uydurulmaz (muhur = olcum). Yalniz
live_secrets_found tur kirilim(lar)i verilir (normalde bos).

Standart: docs/UI_UX_STANDARD.md (invariants §2). Guvenlik-kritik -> opus carve-out.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from typing import Any

from ..vault import cell_crypt, redact

_REDACTION = redact.REDACTION  # "[REDACTED]"


def _mask_type(hit: str) -> str:
    """Mask hit'ini taban tipe indirger: 'phrase:master password' -> 'phrase'."""
    return hit.split(":", 1)[0]


def _decrypt_safe(cell: Any, key: bytes, aad: str):
    """Hucreyi coz; cozulemezse None (sayimda 'undecryptable'). Ham deger DISARI cikmaz."""
    try:
        return cell_crypt.decrypt_cell(cell, key, aad)
    except Exception:
        return None


def _scan_stored(plain: str) -> tuple[int, list[str]]:
    """Saklanan (maskeli) icerik icin (marker_count, live_hits) doner.
    marker_count = '[REDACTED]' sayisi; live_hits = yeniden-tarama sirlari (normalde bos)."""
    marker_count = plain.count(_REDACTION)
    try:
        obj = json.loads(plain)
    except Exception:
        obj = plain
    _red, hits = redact.scan(obj)
    return marker_count, hits


def compute_stats(vault) -> dict:
    """Panonun ozet metriklerini uretir (salt-okunur). Ham icerik dondurmez."""
    conn = vault.get_connection()
    key = vault._db_key
    cur = conn.cursor()

    # --- events ---
    ev_total = ev_distilled = ev_with_markers = 0
    ev_markers = ev_undecryptable = 0
    ev_encrypted = ev_legacy = 0
    live_types: Counter = Counter()
    live_total = 0
    cur.execute("SELECT content, distilled FROM events")
    for row in cur.fetchall():
        ev_total += 1
        if row["distilled"]:
            ev_distilled += 1
        cell = row["content"]
        if cell_crypt.is_encrypted(cell):
            ev_encrypted += 1
        else:
            ev_legacy += 1
        plain = _decrypt_safe(cell, key, cell_crypt.aad_event())
        if plain is None:
            ev_undecryptable += 1
            continue
        markers, hits = _scan_stored(plain)
        if markers:
            ev_with_markers += 1
            ev_markers += markers
        for h in hits:
            live_total += 1
            live_types[_mask_type(h)] += 1

    # --- profile ---
    pr_keys = pr_markers = pr_undecryptable = 0
    pr_encrypted = pr_legacy = 0
    pr_live = 0
    cur.execute("SELECT key, value FROM profile")
    for row in cur.fetchall():
        pr_keys += 1
        cell = row["value"]
        if cell_crypt.is_encrypted(cell):
            pr_encrypted += 1
        else:
            pr_legacy += 1
        plain = _decrypt_safe(cell, key, cell_crypt.aad_profile(row["key"]))
        if plain is None:
            pr_undecryptable += 1
            continue
        markers, hits = _scan_stored(plain)
        pr_markers += markers
        for h in hits:
            pr_live += 1
            live_total += 1
            live_types[_mask_type(h)] += 1

    # --- audit ---
    cur.execute("SELECT COUNT(*) AS n FROM audit")
    au_records = cur.fetchone()["n"]
    try:
        chain_valid = bool(vault.audit_chain.verify_chain()) if vault.audit_chain else None
    except Exception:
        chain_valid = None
    cur.execute("SELECT details FROM audit")
    au_encrypted = au_legacy = 0
    for row in cur.fetchall():
        if cell_crypt.is_encrypted(row["details"]):
            au_encrypted += 1
        else:
            au_legacy += 1

    # --- at-rest kapsama (durust; ADR 0003) ---
    total_cells = ev_encrypted + ev_legacy + pr_encrypted + pr_legacy + au_encrypted + au_legacy
    encrypted_cells = ev_encrypted + pr_encrypted + au_encrypted
    legacy_cells = ev_legacy + pr_legacy + au_legacy
    cell_status = "full" if legacy_cells == 0 and total_cells > 0 else (
        "partial" if encrypted_cells > 0 else "none")

    return {
        "generated_at": time.time(),
        "events": {
            "total": ev_total,
            "distilled": ev_distilled,
            "pending": ev_total - ev_distilled,
            "with_secrets": ev_with_markers,
            "masked_markers": ev_markers,
            "undecryptable": ev_undecryptable,
        },
        "profile": {
            "keys": pr_keys,
            "masked_markers": pr_markers,
            "undecryptable": pr_undecryptable,
        },
        "audit": {
            "records": au_records,
            "chain_valid": chain_valid,
        },
        "redaction": {
            # Toplam maskelenmis sir isaretcisi (event + profile).
            "masked_markers": ev_markers + pr_markers,
            # Yeniden-tarama sirlari: kapidan gecmis veride 0 OLMALI (>0 = legacy plaintext uyarisi).
            "live_secrets_found": live_total,
            "live_by_type": dict(live_types),
        },
        "at_rest": {
            # app-layer per-cell AES-256-GCM (cell_crypt); tam-DB DEGIL.
            "cell_encryption": {
                "algo": "AES-256-GCM",
                "status": cell_status,
                "encrypted_cells": encrypted_cells,
                "legacy_plaintext_cells": legacy_cells,
                "total_cells": total_cells,
            },
            # Tam-dosya at-rest: SQLCipher HENUZ muhurlu degil (toolchain; ADR 0003).
            "full_db": {"scheme": "SQLCipher", "status": "pending"},
            "key_management": {"scheme": "Windows DPAPI", "status": "protected"},
        },
    }


def profile_entries(vault, limit: int = 200) -> list[dict]:
    """Kalici profil kayitlarinin MASKELI okumasi (owner Profile gorunumu, IA §5.3).
    value redact.scan'den gecirilir (yazimda zaten maskeli + burada savunma-derinligi) ->
    maskeli deger owner'a gosterilir; ham sir sizmaz. provenance = event-ID sayisi."""
    limit = max(1, min(int(limit), 1000))
    conn = vault.get_connection()
    key = vault._db_key
    cur = conn.cursor()
    cur.execute(
        "SELECT key, value, provenance, updated_at FROM profile ORDER BY key LIMIT ?",
        (limit,),
    )
    out: list[dict] = []
    for row in cur.fetchall():
        plain = _decrypt_safe(row["value"], key, cell_crypt.aad_profile(row["key"]))
        if plain is None:
            masked_value, markers, readable = None, 0, False
        else:
            try:
                obj = json.loads(plain)
            except Exception:
                obj = plain
            masked_value, _hits = redact.scan(obj)  # savunma-derinligi: sir varsa maskele
            markers = plain.count(_REDACTION)
            readable = True
        try:
            prov = json.loads(row["provenance"])
            prov_n = len(prov) if isinstance(prov, list) else 0
        except Exception:
            prov_n = 0
        out.append({
            "key": row["key"],
            "value": masked_value,
            "provenance_count": prov_n,
            "updated_at": row["updated_at"],
            "masked": markers > 0,
            "readable": readable,
        })
    return out


def recent_events(vault, limit: int = 20) -> list[dict]:
    """Son olaylarin MASKELI yapisal ozeti. 'content' alani DONDURULMEZ (yalniz metadata +
    maske durumu). source/type metadata olsa da savunma-derinligi icin redact'ten gecirilir."""
    limit = max(1, min(int(limit), 100))
    conn = vault.get_connection()
    key = vault._db_key
    cur = conn.cursor()
    cur.execute(
        "SELECT id, timestamp, source, type, content FROM events ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    out: list[dict] = []
    for row in cur.fetchall():
        plain = _decrypt_safe(row["content"], key, cell_crypt.aad_event())
        markers = plain.count(_REDACTION) if plain is not None else 0
        safe_source, _h = redact.redact_text(row["source"] or "")
        out.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "type": row["type"],
            "source": safe_source,
            "masked": markers > 0,
            "masked_markers": markers,
            "readable": plain is not None,
        })
    return out
