import os
import json

_BROWSER_CONFIG_PATH = "d:/kasa/browser_config.json"

def _read_browser_config():
    try:
        with open(_BROWSER_CONFIG_PATH, 'r') as file:
            return json.load(file)
    except Exception as e:
        print("[KASA] browser config okuma hatasi:", str(e))
        return {"proxy_enabled": False, "proxy_address": ""}

def _apply_proxy_env():
    cfg = _read_browser_config()
    addr = (cfg.get("proxy_address") or "").strip()
    if cfg.get("proxy_enabled") and addr:
        os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--proxy-server=" + addr
        print("[KASA] proxy aktif: " + addr)
    else:
        print("[KASA] proxy kapali.")

class KasaApi:
    def get_proxy(self):
        return _read_browser_config()

    def set_proxy(self, enabled, address):
        try:
            with open(_BROWSER_CONFIG_PATH, 'w') as file:
                json.dump({"proxy_enabled": bool(enabled), "proxy_address": str(address or "")}, file)
            print("[KASA] proxy ayarlari guncellendi.")
            _apply_proxy_env()
            return {"proxy_enabled": bool(enabled), "proxy_address": str(address or "")}
        except Exception as e:
            print("[KASA] set_proxy hata:", str(e))
            return {"proxy_enabled": False, "proxy_address": ""}
