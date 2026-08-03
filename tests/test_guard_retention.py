# -*- coding: utf-8 -*-
"""guard.backup() retention: SINIRLI SINK regresyonu. Merkezi arsive tasimak tek basina yetmez;
her iterasyon uretim SINIRLANMALI yoksa arsiv (musfettisin kor noktasi) sinirsiz buyur."""
import os
import sys

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _os.path.join(_KASA_ROOT, "_orch/loop"))
import guard


def test_backup_keeps_only_last_n_per_basename(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "_BAK_DIR", str(tmp_path))
    monkeypatch.setattr(guard, "_BAK_KEEP", 3)
    # Timestamp'i deterministik + artan yap (saniye cozunurlugu cakismasin diye).
    seq = {"n": 0}

    def fake_strftime(_fmt):
        seq["n"] += 1
        return f"20260101_0000{seq['n']:02d}"

    monkeypatch.setattr(guard.time, "strftime", fake_strftime)

    src = tmp_path / "x.py"
    src.write_text("v", encoding="utf-8")
    for _ in range(6):
        guard.backup(str(src))

    remaining = sorted(f for f in os.listdir(tmp_path) if f.startswith("x.py.bak_loop_"))
    assert len(remaining) == 3, f"retention tutmadi: {remaining}"
    # En YENI 3 tutulmali (04,05,06); eskiler (01,02,03) age-out.
    assert remaining == [
        "x.py.bak_loop_20260101_000004",
        "x.py.bak_loop_20260101_000005",
        "x.py.bak_loop_20260101_000006",
    ]


def test_backup_returns_written_path_and_restore_roundtrips(monkeypatch, tmp_path):
    # Retention'a ragmen backup->restore hala calismali (loop rollback bozulmasin).
    monkeypatch.setattr(guard, "_BAK_DIR", str(tmp_path / "arch"))
    src = tmp_path / "y.py"
    src.write_text("orijinal", encoding="utf-8")
    bak = guard.backup(str(src))
    assert os.path.exists(bak)
    src.write_text("bozuldu", encoding="utf-8")
    guard.restore(str(src), bak)
    assert src.read_text(encoding="utf-8") == "orijinal"
