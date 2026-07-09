# -*- coding: utf-8 -*-
"""
L1 secret-allowlist icin KALICI negatif-vaka testleri (Controller).
Kanit yuku: allowlist bir GERCEK secret'i (bearer_token) ASLA gizleyememeli ve
allowlist kaldirilinca/bir fixture disi secret eklenince FAIL uretmeli.
"tek sefer kanitla" degil "surekli kanitla" — false-PASS avi.
"""
import sys
sys.path.insert(0, "d:/kasa")
from tools.security_bench.checks import scan


# bearer_token'in detect-secrets'te goründügü hal: kasa.toml + Base64 High Entropy String.
REAL_TOKEN_FINDING = {"kasa.toml": [{"type": "Base64 High Entropy String", "line_number": 4}]}


def test_real_bearer_token_is_never_suppressed():
    """kasa.toml token'i allowlist'te OLMADIGI icin, tam gercek allowlist ile bile 'real'de kalmali."""
    allow = scan.load_allowlist()  # gercek secret_allowlist.json
    real, suppressed = scan.filter_secrets(REAL_TOKEN_FINDING, allow)
    assert any("kasa.toml" in r for r in real), f"bearer_token gizlendi! real={real}"
    assert suppressed == 0


def test_allowlist_actually_suppresses_known_fixture():
    """Bilinen fixture (red-team) allowlist ile bastirilmali — allowlist gercekten calisiyor."""
    allow = scan.load_allowlist()
    fixture = {"_orch\\redteam\\ai_test_auth.json": [{"type": "Hex High Entropy String", "line_number": 1}]}
    real, suppressed = scan.filter_secrets(fixture, allow)
    assert real == [] and suppressed == 1


def test_empty_allowlist_is_fail_closed():
    """Allowlist bos olursa (dosya okunamaz) HICBIR sey bastirilmamali (fail-closed = daha cok FAIL)."""
    real, suppressed = scan.filter_secrets(REAL_TOKEN_FINDING, set())
    assert suppressed == 0 and len(real) == 1


def test_new_secret_in_non_allowlisted_path_trips():
    """Allowlist'te olmayan bir yola sahte secret eklenirse 'real'e dusmeli (negatif kontrol)."""
    allow = scan.load_allowlist()
    planted = {"src/mcp_server/server.py": [{"type": "Secret Keyword", "line_number": 99}]}
    real, suppressed = scan.filter_secrets(planted, allow)
    assert len(real) == 1 and suppressed == 0


def test_same_file_different_type_not_hidden():
    """Allowlist (path,type) ciftine baglidir: allowlist'li dosyada FARKLI tip yeni secret gizlenmemeli."""
    allow = scan.load_allowlist()
    # run.py Base64 allowlist'li; ama ayni dosyada bir 'Secret Keyword' cikarsa YAKALANMALI.
    mixed = {"tools/security_bench/run.py": [
        {"type": "Base64 High Entropy String", "line_number": 43},  # allowlist'li (GUID)
        {"type": "Secret Keyword", "line_number": 999},             # allowlist DISI -> real
    ]}
    real, suppressed = scan.filter_secrets(mixed, allow)
    assert suppressed == 1 and len(real) == 1 and "Secret Keyword" in real[0]
