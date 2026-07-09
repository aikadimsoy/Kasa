import os, json

_BROWSER_CONFIG_PATH = "d:/kasa/browser_config.json"

def _read_browser_config():
    try:
        with open(_BROWSER_CONFIG_PATH, 'r') as file:
            return json.load(file)
    except Exception as e:
        print("[KASA] read_browser_config hata:", str(e))
        return {"proxy_enabled": False, "proxy_address": ""}

def _level_prelude_js():
    cfg = _read_browser_config()
    lvl = cfg.get("privacy_level") or "strict"
    if lvl not in ("off", "standard", "strict", "paranoid"):
        lvl = "strict"
    return 'window.__KASA_LEVEL__=' + json.dumps(lvl) + ';'

class KasaApi:
    def get_level(self):
        return _read_browser_config().get("privacy_level") or "strict"

    def set_level(self, level):
        allowed = ("off", "standard", "strict", "paranoid")
        lvl = level if level in allowed else "strict"
        cfg = _read_browser_config()  # READ existing config
        cfg["privacy_level"] = lvl
        try:
            with open(_BROWSER_CONFIG_PATH, 'w') as file:
                json.dump(cfg, file)
            return lvl
        except Exception as e:
            print("[KASA] set_level hata:", str(e))
            return "strict"
