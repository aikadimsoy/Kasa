# kasa/tests/test_terms_gate.py

"""
Kullanim sartlari kapisi e2e testleri.
Invariantlar: kabul BEARER ister; kabul diske yazilir + durum doner; /terms sayfasi token
enjekte edilmis + DIS kaynak icermez (air-gap); kabul edilmeden durum accepted=False.
"""

import importlib
import sys

import pytest

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _KASA_ROOT)

from src.desktop import consent


@pytest.fixture
def client(tmp_path, monkeypatch):
    cfg = tmp_path / "kasa.toml"
    monkeypatch.setenv("KASA_CONFIG", str(cfg))
    monkeypatch.setenv("KASA_VAULT_PATH", str(tmp_path / "vault"))
    import src.mcp_server.server as srv
    importlib.reload(srv)
    from fastapi.testclient import TestClient
    c = TestClient(srv.app, raise_server_exceptions=False)
    return c, srv._BEARER_TOKEN


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_status_initially_not_accepted(client):
    c, token = client
    r = c.get("/v1/terms/status", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["accepted"] is False


def test_accept_records_and_flips_status(client, tmp_path):
    c, token = client
    r = c.post("/v1/terms/accept", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # Diske yazildi.
    assert (tmp_path / "acceptance.json").is_file()
    # Durum artik accepted.
    r2 = c.get("/v1/terms/status", headers=_auth(token))
    assert r2.json()["accepted"] is True
    # consent modulu de ayni dosyayi gorur (launch.py bununla start-URL secer).
    assert consent.is_accepted() is True


def test_accept_requires_bearer(client):
    c, _ = client
    r = c.post("/v1/terms/accept")
    assert r.status_code in (401, 403)


def test_status_requires_bearer(client):
    c, _ = client
    r = c.get("/v1/terms/status")
    assert r.status_code in (401, 403)


def test_terms_page_served_and_token_injected(client):
    c, token = client
    r = c.get("/terms")
    assert r.status_code == 200
    body = r.text
    assert token in body                 # server-tarafi token enjekte edildi
    assert "__KASA_TOKEN__" not in body   # placeholder degistirildi
    # Air-gap: sayfa DIS kaynak (http/https CDN) YUKLEMEZ. Guvenli disari-URL sadece MS
    # indirme baglantilaridir ve onlar terms.html'de degil (preflight'ta). Burada hic olmamali.
    assert "http://" not in body and "https://" not in body


def test_terms_version_consistency():
    # consent.TERMS_VERSION, TERMS_OF_USE.md surumuyle ayni olmali (surum kaymasi = sessiz hata).
    text = open(_os.path.join(_KASA_ROOT, "TERMS_OF_USE.md"), encoding="utf-8").read()
    assert f"Sürüm {consent.TERMS_VERSION}" in text
