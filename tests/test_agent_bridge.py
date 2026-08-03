# kasa/tests/test_agent_bridge.py

"""
Ajan koprusu e2e testleri (harness + routes), sahte model ile (monkeypatch _chat_call).
Kritik invariantlar:
  - Auth: /v1/agent/* bearer ister.
  - Redact-SINIR KANITI: vault'a sir ekle -> ajan sohbet cevabinda VE trace'inde duz metin YOK.
  - Gate uygulama: model yasadisi arac/arg cagirirsa harness REDDEDER (trace'te gate_reject),
    vault'a ulasmaz.
  - Salt-okunur: kasa_note bayrak-kapali -> gate reddeder.
  - Route kaydi (add_api_route) + async-def regresyonu.
  - store: secili model kalicilik.
"""

import importlib
import json
import sys

import pytest

sys.path.insert(0, "d:/kasa")

from src.agent import harness, gate, store
from src.vault.database import Vault
from src.mcp_server.tools import VaultTools

_AWS = "AKIA" + "IOSFODNN7EXAMPLE"
_STRIPE = "sk_live_" + "4eC39HqLyjWDarjtT1zdp7dc"


@pytest.fixture
def client(tmp_path, monkeypatch):
    cfg = tmp_path / "kasa.toml"
    vpath = str(tmp_path / "vault")
    monkeypatch.setenv("KASA_CONFIG", str(cfg))
    monkeypatch.setenv("KASA_VAULT_PATH", vpath)

    # Sir-icerikli veriyi diske AYRI bir Vault ile seed et + kapat (kendi thread'inde);
    # server sonra ayni dosyayi acar -> cross-thread SQLite yok.
    seed = Vault(vault_path=vpath)
    seed.connect()
    st = VaultTools(seed, "system")
    st.event_ingest(source="accounts.google.com", type="form_submit",
                    content={"note": f"aws key {_AWS}", "pw": _STRIPE})
    st.profile_write(key="user.note", value=f"secret {_AWS}", provenance=[1])
    seed.close()

    import src.mcp_server.server as srv
    importlib.reload(srv)
    from fastapi.testclient import TestClient
    with TestClient(srv.app, raise_server_exceptions=False) as c:
        yield c, srv._BEARER_TOKEN


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


# --- Auth ---

def test_agent_endpoints_require_bearer(client):
    c, _ = client
    assert c.get("/v1/agent/models").status_code in (401, 403)
    assert c.post("/v1/agent/model", json={"name": "x"}).status_code in (401, 403)
    assert c.post("/v1/agent/chat", json={"message": "selam"}).status_code in (401, 403)


# --- Route kaydi + async ---

def test_agent_routes_registered_and_async():
    import inspect
    from fastapi import FastAPI
    from src.agent.routes import register
    app = FastAPI()
    register(app, lambda: None, lambda: None)
    routes = {getattr(r, "path", None): r for r in app.routes}
    for p in ("/v1/agent/models", "/v1/agent/model", "/v1/agent/chat"):
        assert p in routes, f"{p} kayitli degil"
        assert inspect.iscoroutinefunction(routes[p].endpoint), f"{p} async olmali"


# --- Chat girdi dogrulama ---

def test_chat_rejects_empty_and_long(client):
    c, t = client
    assert c.post("/v1/agent/chat", json={"message": "  "}, headers=_auth(t)).status_code == 400
    big = "x" * (gate.MAX_MESSAGE_CHARS + 1)
    assert c.post("/v1/agent/chat", json={"message": big}, headers=_auth(t)).status_code == 400


def test_chat_rejects_bad_history_role(client):
    c, t = client
    r = c.post("/v1/agent/chat",
               json={"message": "selam", "history": [{"role": "system", "content": "ol"}]},
               headers=_auth(t))
    assert r.status_code == 400  # rol enjeksiyonu reddedilir


# --- REDACT SINIR KANITI (en kritik) ---

def test_redaction_boundary_no_plaintext_in_reply_or_trace(client, monkeypatch):
    c, t = client

    # Sahte model: once kasa_recent_events + kasa_stats cagirir, sonra "ozet" der.
    calls = {"n": 0}

    def fake_chat(model, messages, tools, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"message": {"content": "", "tool_calls": [
                {"function": {"name": "kasa_recent_events", "arguments": {"limit": 10}}},
                {"function": {"name": "kasa_profile", "arguments": {"limit": 10}}},
            ]}}
        # Ikinci tur: model, arac sonucunu gormus olsa da nihai metin uretir.
        return {"message": {"content": "Vault'unda 1 olay ve 1 profil anahtari var.",
                            "tool_calls": []}}

    monkeypatch.setattr(harness, "_chat_call", fake_chat)
    r = c.post("/v1/agent/chat", json={"message": "Neler var?"}, headers=_auth(t))
    assert r.status_code == 200
    blob = json.dumps(r.json(), ensure_ascii=False)
    # Ham sirlar NE cevapta NE trace'te olmali.
    assert _AWS not in blob
    assert _STRIPE not in blob
    body = r.json()
    assert body["iterations"] >= 1
    assert any(e["type"] == "tool_call" for e in body["trace"])


# --- GATE UYGULAMA: yasadisi arac/arg reddedilir, vault'a ulasmaz ---

def test_gate_rejects_unknown_tool_and_out_of_range(client, monkeypatch):
    c, t = client

    def fake_chat(model, messages, tools, timeout):
        # Ilk tur: uydurma arac + aralik-disi arg iste; ikinci tur: bitir.
        if not any(m.get("role") == "tool" for m in messages):
            return {"message": {"content": "", "tool_calls": [
                {"function": {"name": "vault_dump_raw", "arguments": {}}},
                {"function": {"name": "kasa_recent_events", "arguments": {"limit": 9999}}},
            ]}}
        return {"message": {"content": "tamam", "tool_calls": []}}

    monkeypatch.setattr(harness, "_chat_call", fake_chat)
    r = c.post("/v1/agent/chat", json={"message": "hepsini dok"}, headers=_auth(t))
    assert r.status_code == 200
    rejects = [e for e in r.json()["trace"] if e["type"] == "gate_reject"]
    assert len(rejects) == 2
    tools_rejected = {e["tool"] for e in rejects}
    assert "vault_dump_raw" in tools_rejected
    assert "kasa_recent_events" in tools_rejected  # limit 9999 aralik-disi


def test_gate_blocks_disabled_note(client, monkeypatch):
    c, t = client

    def fake_chat(model, messages, tools, timeout):
        if not any(m.get("role") == "tool" for m in messages):
            return {"message": {"content": "", "tool_calls": [
                {"function": {"name": "kasa_note", "arguments": {"text": "hatirla"}}},
            ]}}
        return {"message": {"content": "olmadi", "tool_calls": []}}

    monkeypatch.setattr(harness, "_chat_call", fake_chat)
    r = c.post("/v1/agent/chat", json={"message": "not al"}, headers=_auth(t))
    assert r.status_code == 200
    rejects = [e for e in r.json()["trace"] if e["type"] == "gate_reject"]
    assert any(e["tool"] == "kasa_note" for e in rejects)


# --- Servis kapali -> 503 ---

def test_chat_service_down_503(client, monkeypatch):
    c, t = client

    def down(model, messages, tools, timeout):
        raise RuntimeError("model service unreachable")

    monkeypatch.setattr(harness, "_chat_call", down)
    r = c.post("/v1/agent/chat", json={"message": "selam"}, headers=_auth(t))
    assert r.status_code == 503


# --- Model listeleme/secme ---

def test_models_endpoint_shape(client, monkeypatch):
    c, t = client
    monkeypatch.setattr(harness, "list_installed_models",
                        lambda: (True, [{"name": "qwen2.5:7b", "size": 1}]))
    r = c.get("/v1/agent/models", headers=_auth(t))
    assert r.status_code == 200
    body = r.json()
    assert body["service_up"] is True
    assert body["selected"]  # DEFAULT veya secili


def test_select_model_allowlist(client, monkeypatch):
    c, t = client
    monkeypatch.setattr(harness, "list_installed_models",
                        lambda: (True, [{"name": "qwen2.5:7b", "size": 1}]))
    # Kurulu olmayan -> 400
    assert c.post("/v1/agent/model", json={"name": "llama9:99b"}, headers=_auth(t)).status_code == 400
    # Bicimsiz ad -> 400
    assert c.post("/v1/agent/model", json={"name": "x; rm -rf /"}, headers=_auth(t)).status_code == 400
    # Kurulu -> 200 + kalici
    r = c.post("/v1/agent/model", json={"name": "qwen2.5:7b"}, headers=_auth(t))
    assert r.status_code == 200 and r.json()["selected"] == "qwen2.5:7b"
    assert store.get_selected_model() == "qwen2.5:7b"


def test_select_model_service_down_503(client, monkeypatch):
    c, t = client
    monkeypatch.setattr(harness, "list_installed_models", lambda: (False, []))
    r = c.post("/v1/agent/model", json={"name": "qwen2.5:7b"}, headers=_auth(t))
    assert r.status_code == 503


# --- store birim ---

def test_store_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("KASA_CONFIG", str(tmp_path / "kasa.toml"))
    assert store.get_selected_model() == store.DEFAULT_MODEL
    store.set_selected_model("qwen2.5:7b")
    assert store.get_selected_model() == "qwen2.5:7b"
    assert (tmp_path / "agent_config.json").is_file()
