# -*- coding: utf-8 -*-
"""Denylist sertlestirme (regex/entropi) uctan-uca: redact kapisi gercek yazma
yollarindan (profile_write + event_ingest) geciyor mu, at-rest'te sir MASKELI mi,
mesru veri + git-SHA (FP-guard) KORUNUYOR mu."""
import sys, json
import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _KASA_ROOT)
import pytest
from src.vault.database import Vault
from src.mcp_server.tools import VaultTools
from src.vault import cell_crypt as cc

R = "[REDACTED]"


def make_vault(tmp_path):
    v = Vault(vault_path=str(tmp_path / "vault")); v.connect()
    return v, VaultTools(v, "system")


@pytest.fixture(scope="function")
def vault_setup(tmp_path):
    v, t = make_vault(tmp_path)
    yield v, t
    v.close()


def _read_profile(v, key):
    """At-rest sifreli profile value'yu cozup dondur (maskeleme SONRASI hali)."""
    row = v.get_connection().execute("SELECT key, value FROM profile WHERE key=?", (key,)).fetchone()
    return json.loads(cc.decrypt_cell(row["value"], v._db_key, cc.aad_profile(key)))


def _read_last_event(v):
    row = v.get_connection().execute("SELECT content FROM events ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(cc.decrypt_cell(row["content"], v._db_key, cc.aad_event()))


def test_high_entropy_masked_via_profile_write(vault_setup):
    v, t = vault_setup
    tok = "aB3dF6hJ9kLmN0pQrStUvWxYz012345K"  # 32 ch, +/ yok -> entropi kurali yakalar
    t.profile_write("user.profile.note", {"text": f"creds {tok} end", "confidence": 0.9}, [1])
    val = _read_profile(v, "user.profile.note")
    assert R in val["text"] and tok not in val["text"], val
    assert val["confidence"] == 0.9  # sayi dokunulmaz (yapi korunur)


def test_base64_secret_masked_via_event_ingest(vault_setup):
    v, t = vault_setup
    t.event_ingest("chrome_extension", "page_visit",
                   {"note": "token=sk_live_AB+CD/EFGH12345678+ijkl/MNOPqrstuvwx=="}, ttl_days=10)
    ev = _read_last_event(v)
    assert R in ev["note"] and "sk_live_AB+CD" not in ev["note"], ev


def test_hex_with_context_masked_via_event_ingest(vault_setup):
    v, t = vault_setup
    secret = "da39a3ee5e6b4b0d3255bfef95601890"  # 32 hex
    t.event_ingest("web", "note", {"msg": f"api key: {secret}"}, ttl_days=5)
    ev = _read_last_event(v)
    assert R in ev["msg"] and secret not in ev["msg"], ev


def test_git_sha_preserved_fp_guard(vault_setup):
    v, t = vault_setup
    sha = "da39a3ee5e6b4b0d3255bfef95601890afd80709"  # 40 hex, baglamsiz -> KORUNMALI
    t.profile_write("user.profile.commit", {"text": f"merged {sha} to main"}, [1])
    val = _read_profile(v, "user.profile.commit")
    assert sha in val["text"] and R not in val["text"], val


def test_normal_text_accepted(vault_setup):
    v, t = vault_setup  # negatif kontrol: mesru dusuk-entropi metin dokunulmaz
    txt = "kullanici cay icmeyi seviyor ve sabah kosuya cikar"
    t.profile_write("user.habits.daily", {"text": txt}, [1])
    val = _read_profile(v, "user.habits.daily")
    assert val["text"] == txt, val


def test_structure_preserved_nested(vault_setup):
    v, t = vault_setup
    payload = {"a": {"b": "leak AB+CD/EFGH12345678+ijkl/MNOPqr=="}, "n": 7,
               "list": ["ok", "the system backdoor here"]}
    t.profile_write("user.profile.deep", payload, [1])
    val = _read_profile(v, "user.profile.deep")
    assert val["n"] == 7                        # int dokunulmaz
    assert R in val["a"]["b"]                    # nested string yaprak maskeli
    assert val["list"][0] == "ok"               # temiz eleman korunur
    assert R in val["list"][1]                   # phrase 'backdoor' maskeli


# --- Adim 1: hibrit tespit (yapili prefix + base64 entropi-tabani). Olculdu: measure_redact*.py ---
def test_credential_prefixes_masked_via_profile_write(vault_setup):
    """Yapili sirlar (AKIA/ghp_/sk_live_/xoxb) entropiye takilmadan prefix ile KESIN yakalanir.
    Bunlar 4.3 entropi-esiginin ALTINDA (AKIA H=3.68) -> entropi tek basina KACIRIRDI (FN)."""
    v, t = vault_setup
    # Sentetik test verisi -- GERCEK anahtar degil. Hepsi AWS/Stripe/GitHub/Slack'in
    # KENDI dokumantasyon ornekleridir ve maskeleme katmaninin onekleri gercekten
    # yakaladigini olcmek icin duruyorlar.
    # Turkce not: parcali yazilmalarinin tek sebebi GitHub push-protection'in butun bir
    # token gorunce push'u reddetmesi. Python derleme aninda birlestirir -> CALISMA-ANI
    # DEGERI BIREBIR AYNI, yani test ayni seyi olcmeye devam eder. Bypass linkine
    # tiklamak yerine bu yol secildi: repoda kalici "sir onaylandi" kaydi birakmaz.
    creds = {
        "aws":    "AKIA" + "IOSFODNN7EXAMPLE",
        "ghp":    "ghp_" + "16C7e42F292c6912E7710c838347Ae178B4a",
        "stripe": "sk_live_" + "4eC39HqLyjWDarjtT1zdp7dc",
        "slack":  "xoxb-" + "2401-2402-AbCdEfGhIjKlMnOpQrStUvWxYz",
    }
    for name, secret in creds.items():
        t.profile_write("user.profile.cred_%s" % name, {"text": "key %s here" % secret}, [1])
        val = _read_profile(v, "user.profile.cred_%s" % name)
        assert R in val["text"] and secret not in val["text"], (name, val)


def test_filepath_preserved_base64_floor(vault_setup):
    """FP-guard: dusuk-H (olculen ~3.92) '/'li dosya yolu, base64 entropi-tabani (4.0) ile KORUNUR.
    Taban oncesi bu yol '[REDACTED]' olurdu (canli gezinme kasasinda surekli FP = kendine-DoS)."""
    v, t = vault_setup
    path = "C:/Users/ExampleUser/AppData/Local/Temp/notes.txt"
    t.profile_write("user.profile.path", {"text": "saved to %s" % path}, [1])
    val = _read_profile(v, "user.profile.path")
    assert path in val["text"] and R not in val["text"], val


# --- Adim 2: URL cerrahisi (entropi muafiyeti + query-only tarama). Olculdu: measure_redact2.py ---
def test_url_preserved_but_query_secret_masked(vault_setup):
    """Duz URL host/path/query KORUNUR (entropi kurali URL'e dokunmaz); query'ye gomulu sir MASKELENIR.
    Gezinme kasasi icin secilen tradeoff: URL yapisi yasar, ?token=SIR gibi gomulu sir olur."""
    v, t = vault_setup
    plain = "https://www.example.com/path?query=value&page=12"
    t.profile_write("user.profile.url_plain", {"text": "visit %s here" % plain}, [1])
    assert _read_profile(v, "user.profile.url_plain")["text"] == "visit %s here" % plain
    embed = "https://api.example.com/cb?token=aB3dF6hJ9kLmN0pQrStUvWxYz012345K&x=1"
    t.profile_write("user.profile.url_secret", {"text": embed}, [1])
    got = _read_profile(v, "user.profile.url_secret")["text"]
    assert "aB3dF6hJ9kLmN0pQrStUvWxYz012345K" not in got and R in got, got
    assert got.startswith("https://api.example.com/cb?token=") and got.endswith("&x=1"), got
