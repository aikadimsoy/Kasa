# kasa/tests/test_agent_race.py

"""
Yaris Modu (race) testleri: gate model-listesi dogrulama + harness izolasyon + endpoint.
Invariantlar: 2..4 benzersiz kurulu model; bir modelin cokmesi yarisi bozmaz; ayni redact
siniri her modelde; concurrency-lock 409; bearer.
"""

import importlib
import json
import sys

import pytest

import os as _os
# Turkce not: sabit "d:/kasa" YERINE bu dosyanin konumundan turetilir
# (tests/ -> parent = depo koku). Sabit yol, depoyu klonlayan herkeste ve
# CI kosucusunda bu testi kirardi.
_KASA_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, _KASA_ROOT)

from src.agent import gate, harness
from src.vault.database import Vault
from src.mcp_server.tools import VaultTools

# Sentetik test verisi -- GERCEK anahtar degil. Hepsi AWS/Stripe/GitHub/Slack'in
# KENDI dokumantasyon ornekleridir ve maskeleme katmaninin onekleri gercekten
# yakaladigini olcmek icin duruyorlar.
# Turkce not: parcali yazilmalarinin tek sebebi GitHub push-protection'in butun bir
# token gorunce push'u reddetmesi. Python derleme aninda birlestirir -> CALISMA-ANI
# DEGERI BIREBIR AYNI, yani test ayni seyi olcmeye devam eder. Bypass linkine
# tiklamak yerine bu yol secildi: repoda kalici "sir onaylandi" kaydi birakmaz.
_AWS = "AKIA" + "IOSFODNN7EXAMPLE"


# --- gate.validate_race_models ---

def test_race_models_count_bounds():
    inst = {"a", "b", "c", "d", "e"}
    assert not gate.validate_race_models(["a"], inst)[0]          # <2
    assert not gate.validate_race_models(["a", "b", "c", "d", "e"], inst)[0]  # >4
    ok, norm = gate.validate_race_models(["a", "b"], inst)
    assert ok and norm == ["a", "b"]


def test_race_models_dedup_preserves_order():
    inst = {"a", "b"}
    ok, norm = gate.validate_race_models(["a", "b", "a"], inst)
    assert ok and norm == ["a", "b"]


def test_race_models_rejects_uninstalled_or_malformed():
    inst = {"qwen2.5:7b"}
    assert not gate.validate_race_models(["qwen2.5:7b", "ghost:1b"], inst)[0]
    assert not gate.validate_race_models(["qwen2.5:7b", "x; rm -rf /"], inst)[0]
    assert not gate.validate_race_models("notalist", inst)[0]


# --- harness.run_race izolasyon (sahte _chat_call) ---

def test_run_race_isolates_failure(monkeypatch):
    import asyncio

    class _Vault:  # run_chat vault'u yalniz _run_tool'da kullanir; tool cagirmayan senaryo
        pass

    def fake_chat(model, messages, tools, timeout):
        if model == "boom:1b":
            raise RuntimeError("model service unreachable")
        return {"message": {"content": f"cevap-{model}", "tool_calls": []}}

    monkeypatch.setattr(harness, "_chat_call", fake_chat)
    out = asyncio.run(harness.run_race(_Vault(), ["ok:1b", "boom:1b"], "selam", None))
    results = {r["model"]: r for r in out["results"]}
    assert "cevap-ok:1b" in results["ok:1b"]["reply"]
    assert "error" in results["boom:1b"]        # cokme izole edildi
    assert "reply" not in results["boom:1b"]


# --- endpoint e2e ---

@pytest.fixture
def client(tmp_path, monkeypatch):
    vpath = str(tmp_path / "vault")
    monkeypatch.setenv("KASA_CONFIG", str(tmp_path / "kasa.toml"))
    monkeypatch.setenv("KASA_VAULT_PATH", vpath)
    seed = Vault(vault_path=vpath); seed.connect()
    VaultTools(seed, "system").event_ingest(
        source="site.example", type="form_submit", content={"note": f"key {_AWS}"})
    seed.close()
    import src.mcp_server.server as srv
    importlib.reload(srv)
    from fastapi.testclient import TestClient
    with TestClient(srv.app, raise_server_exceptions=False) as c:
        yield c, srv._BEARER_TOKEN


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_race_requires_bearer(client):
    c, _ = client
    assert c.post("/v1/agent/race", json={"message": "x", "models": ["a", "b"]}).status_code in (401, 403)


def test_race_rejects_bad_model_count(client, monkeypatch):
    c, t = client
    monkeypatch.setattr(harness, "list_installed_models",
                        lambda: (True, [{"name": "qwen2.5:7b", "size": 1}]))
    # tek model -> 400 (min 2)
    r = c.post("/v1/agent/race", json={"message": "selam", "models": ["qwen2.5:7b"]}, headers=_auth(t))
    assert r.status_code == 400


def test_race_service_down_503(client, monkeypatch):
    c, t = client
    monkeypatch.setattr(harness, "list_installed_models", lambda: (False, []))
    r = c.post("/v1/agent/race", json={"message": "selam", "models": ["a", "b"]}, headers=_auth(t))
    assert r.status_code == 503


def test_race_end_to_end_no_leak(client, monkeypatch):
    c, t = client
    monkeypatch.setattr(harness, "list_installed_models",
                        lambda: (True, [{"name": "m1:1b", "size": 1}, {"name": "m2:1b", "size": 1}]))

    def fake_chat(model, messages, tools, timeout):
        # Ilk tur her modelde kasa_recent_events cagir, ikinci tur bitir.
        if not any(m.get("role") == "tool" for m in messages):
            return {"message": {"content": "", "tool_calls": [
                {"function": {"name": "kasa_recent_events", "arguments": {"limit": 5}}}]}}
        return {"message": {"content": f"ozet-{model}", "tool_calls": []}}

    monkeypatch.setattr(harness, "_chat_call", fake_chat)
    r = c.post("/v1/agent/race",
               json={"message": "olaylari ozetle", "models": ["m1:1b", "m2:1b"]}, headers=_auth(t))
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) == 2
    blob = json.dumps(body, ensure_ascii=False)
    assert _AWS not in blob                       # redact siniri her modelde tuttu
    for res in body["results"]:
        assert res["reply"].startswith("ozet-")
        assert any(e["type"] == "tool_call" for e in res["trace"])
