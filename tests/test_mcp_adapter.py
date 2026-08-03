# kasa/tests/test_mcp_adapter.py

"""
MCP adaptor proxy cekirdegi testleri (SDK'siz: src/mcp_adapter/proxy.py).
Invariantlar: loopback-disi URL reddi (air-gap), rezerve 'system' agent-id reddi,
sunucu hata detayinin ValueError olarak yuzeye cikmasi, basarili sonucun cozulmesi.
Ayrica grant_agent_scope CLI'nin yukselme kapilari (system + admin:grant reddi).
"""

import io
import json
import sys
import urllib.error

import pytest

sys.path.insert(0, "d:/kasa")

from src.mcp_adapter import proxy


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("KASA_SERVER_URL", raising=False)
    monkeypatch.delenv("KASA_MCP_AGENT_ID", raising=False)
    yield


def test_build_settings_defaults(tmp_path, monkeypatch):
    # KASA_CONFIG'i gecici toml'a yonlendir (load_config onurlanir).
    cfg = tmp_path / "kasa.toml"
    cfg.write_text('[server]\nbearer_token = "tok123"\nhost = "127.0.0.1"\nport = 8000\n',
                   encoding="utf-8")
    monkeypatch.setenv("KASA_CONFIG", str(cfg))
    s = proxy.build_settings()
    assert s["base_url"] == "http://127.0.0.1:8000"
    assert s["agent_id"] == "mcp_client"
    assert s["bearer"] == "tok123"


def test_build_settings_forces_loopback_host(tmp_path, monkeypatch):
    # Config disari bir host dese bile adaptor loopback'e zorlar (air-gap).
    cfg = tmp_path / "kasa.toml"
    cfg.write_text('[server]\nbearer_token = "t"\nhost = "0.0.0.0"\nport = 8000\n',
                   encoding="utf-8")
    monkeypatch.setenv("KASA_CONFIG", str(cfg))
    s = proxy.build_settings()
    assert s["base_url"].startswith("http://127.0.0.1")


def test_build_settings_rejects_external_url_env(tmp_path, monkeypatch):
    cfg = tmp_path / "kasa.toml"
    cfg.write_text('[server]\nbearer_token = "t"\n', encoding="utf-8")
    monkeypatch.setenv("KASA_CONFIG", str(cfg))
    monkeypatch.setenv("KASA_SERVER_URL", "http://evil.example.com:8000")
    with pytest.raises(ValueError, match="loopback"):
        proxy.build_settings()


def test_build_settings_rejects_system_agent(tmp_path, monkeypatch):
    cfg = tmp_path / "kasa.toml"
    cfg.write_text('[server]\nbearer_token = "t"\n', encoding="utf-8")
    monkeypatch.setenv("KASA_CONFIG", str(cfg))
    monkeypatch.setenv("KASA_MCP_AGENT_ID", "system")
    with pytest.raises(ValueError, match="reserved"):
        proxy.build_settings()


def _settings():
    return {"bearer": "tok", "base_url": "http://127.0.0.1:8000", "agent_id": "mcp_client"}


def test_execute_success(monkeypatch):
    captured = {}

    class _Resp:
        def read(self):
            return json.dumps({"results": [{"tool_name": "profile_read",
                                            "result": {"status": "success", "data": []}}]}).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["auth"] = req.headers.get("Authorization")
        captured["body"] = json.loads(req.data.decode())
        return _Resp()

    monkeypatch.setattr(proxy.urllib.request, "urlopen", fake_urlopen)
    out = proxy.execute(_settings(), "profile_read", {"scope": "user.*"})
    assert out == {"status": "success", "data": []}
    assert captured["url"].endswith("/v1/execute_tool")
    assert captured["auth"] == "Bearer tok"
    assert captured["body"]["agent_id"] == "mcp_client"
    assert captured["body"]["tool_calls"][0] == {"tool_name": "profile_read",
                                                 "parameters": {"scope": "user.*"}}


def test_execute_maps_http_error_detail(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, 403, "Forbidden", {},
            io.BytesIO(json.dumps({"detail": "izin yok"}).encode()))

    monkeypatch.setattr(proxy.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ValueError, match=r"HTTP 403.*izin yok"):
        proxy.execute(_settings(), "forget", {"topic": "x"})


def test_execute_maps_unreachable(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("baglanti reddedildi")

    monkeypatch.setattr(proxy.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ValueError, match="unreachable"):
        proxy.execute(_settings(), "audit_read", {})


# --- grant_agent_scope CLI yukselme kapilari ---

def test_grant_cli_refuses_system_and_admin_grant(tmp_path):
    from tools.grant_agent_scope import main
    vault = str(tmp_path / "vault")
    assert main(["grant", "system", "events:write", "--vault", vault]) == 2
    assert main(["grant", "mcp_client", "admin:grant", "--vault", vault]) == 2


def test_grant_cli_grant_list_revoke_roundtrip(tmp_path, capsys):
    from tools.grant_agent_scope import main
    vault = str(tmp_path / "vault")
    assert main(["grant", "mcp_client", "audit:read", "--vault", vault]) == 0
    main(["list", "mcp_client", "--vault", vault])
    out = capsys.readouterr().out
    assert "audit:read" in out and "ACTIVE" in out
    assert main(["revoke", "mcp_client", "audit:read", "--vault", vault]) == 0
    main(["list", "mcp_client", "--vault", vault])
    out = capsys.readouterr().out
    assert "revoked@" in out
