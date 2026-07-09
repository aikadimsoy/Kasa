import json
import pytest
pytest.importorskip("webview")
from src.browser import browser_window as bw

@pytest.fixture
def setup(monkeypatch, tmp_path):
    cfg_path = tmp_path / "browser_config.json"
    monkeypatch.setattr(bw, "_BROWSER_CONFIG_PATH", str(cfg_path))
    with open(cfg_path, 'w') as f:
        json.dump({"privacy_level": "strict", "proxy_enabled": True}, f)
    api = bw.KasaApi()
    monkeypatch.setattr(api, "list_models", lambda: [{"name":"qwen2.5:7b","size":0}])
    return api, cfg_path

def test_set_model_rejects_uninstalled(setup):
    api, cfg_path = setup
    with pytest.raises(ValueError):
        api.set_model("evil-not-installed")
    # Reload the JSON file to check if "agent_model" key is not added
    with open(cfg_path) as f:
        data = json.load(f)
    assert "agent_model" not in data

def test_set_model_writes_and_merges(setup, monkeypatch):
    api, cfg_path = setup
    monkeypatch.setattr(api, "list_models", lambda: [{"name":"hermes3:8b","size":0}])
    assert api.set_model("hermes3:8b") == "hermes3:8b"
    # Reload the JSON file to check if data is merged correctly
    with open(cfg_path) as f:
        data = json.load(f)
    assert data["agent_model"] == "hermes3:8b"
    assert data["privacy_level"] == "strict"
    assert data["proxy_enabled"] is True

def test_get_model_fallback(setup, monkeypatch):
    api, cfg_path = setup
    monkeypatch.setattr(api, "list_models", lambda: [{"name":"hermes3:8b","size":0}])
    assert bw.KasaApi().get_model() == "qwen2.5:7b"
