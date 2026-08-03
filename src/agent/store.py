# kasa/src/agent/store.py

"""
Persist the panel agent's selected local model name in ``agent_config.json`` inside KASA's
data directory (atomic write). Mirrors src/desktop/consent.py's data-dir resolution so the
server and launcher agree on location. Independent of browser_config.json (that module is not
in the exe). No network; JSON only.

Turkce not: Panel ajaninin SECILI yerel model adini KASA veri dizinindeki
agent_config.json'a atomik yazar/okur. Sunucu ile baslatici ayni konumda anlassin diye
consent.py'nin veri-dizini cozumunu yansitir. Ag YOK, yalniz JSON; sir tutmaz.
"""

from __future__ import annotations

import json
import os
import pathlib

DEFAULT_MODEL = "qwen2.5:7b"


def _data_dir() -> pathlib.Path:
    """Kalici veri dizini (consent.py ile ayni kaynak). KASA_CONFIG'in parent'i; yoksa
    KASA_HOME; yoksa %APPDATA%\\KASA (ya da home)."""
    cfg = os.environ.get("KASA_CONFIG")
    if cfg:  # bos string degil (consent.py deseni)
        return pathlib.Path(cfg).resolve().parent
    base = os.environ.get("KASA_HOME") or os.path.join(
        os.environ.get("APPDATA") or str(pathlib.Path.home()), "KASA")
    return pathlib.Path(base)


def config_path() -> pathlib.Path:
    return _data_dir() / "agent_config.json"


def get_selected_model() -> str:
    """Secili modeli dondurur; dosya yok/bozuksa DEFAULT_MODEL."""
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return DEFAULT_MODEL
    return data.get("selected_model") or DEFAULT_MODEL


def set_selected_model(name: str) -> dict:
    """Secili modeli merge-yazar (atomik: temp + replace). Kayit dict'ini dondurur."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (FileNotFoundError, ValueError, OSError):
        data = {}
    data["selected_model"] = name
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return {"selected_model": name}


# --------------------------------------------------------------------------- tek yetkili cozucu
#
# SEBEP: model adi UC ayri yerde tutuluyordu ve ikisi CANLI olarak CELISIYORDU —
#   agent_config.json:selected_model  (sohbet ajani okur)  -> 'qwen2.5vl:7b' (bir GORUNTU modeli)
#   browser_config.json:agent_model   (damitma okur)       -> 'deepseek-coder-v2:16b'
#   kasa.toml [distill] model         (HIC OKUNMUYORDU)    -> olu konfig, sessiz no-op
# SONUC (fixlenmezse): kullanici UI'dan model secer, sohbet ajani baska modeli calistirmaya
# devam eder; secim sessizce etkisiz kalir ve olculen davranis uretimde gecerli olmaz.
# KARAR: tek cozucu + tanimli oncelik. agent_config YETKILI (veri dizini, atomik yazim,
# exe'de de var); browser_config gecis/dev icin; kasa.toml belgelenmis ayar oldugu icin
# SILINMEZ, en dusuk oncelikle BAGLANIR (belgelenmis ama etkisiz ayar = sessiz yalan).

def _browser_config_candidates() -> list[pathlib.Path]:
    """browser_config.json adaylari: env -> veri dizini -> depo koku (dev/legacy)."""
    out: list[pathlib.Path] = []
    env = os.environ.get("KASA_BROWSER_CONFIG")
    if env:
        out.append(pathlib.Path(env))
    out.append(_data_dir() / "browser_config.json")
    out.append(pathlib.Path(__file__).resolve().parent.parent.parent / "browser_config.json")
    return out


def _from_browser_config() -> str | None:
    for path in _browser_config_candidates():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            continue
        if isinstance(data, dict) and data.get("agent_model"):
            return str(data["agent_model"])
    return None


def _from_toml() -> str | None:
    """kasa.toml [distill] model — gec import (dairesel bagimlilik yok), hata yutulur."""
    try:
        from ..config import load_config  # noqa: PLC0415 — kasitli gec import
        cfg_path = os.environ.get("KASA_CONFIG")
        base = pathlib.Path(cfg_path) if cfg_path else (
            pathlib.Path(__file__).resolve().parent.parent.parent / "kasa.toml")
        value = (load_config(base).get("distill") or {}).get("model")
        return str(value) if value else None
    except Exception:
        return None


def resolve_model() -> str:
    """Etkin model adi — TEK kaynak. Oncelik: agent_config > browser_config > kasa.toml > varsayilan.
    Sohbet ajani, damitma ve tarayici bu fonksiyonu kullanir; boylece hepsi AYNI modeli gorur."""
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("selected_model"):
            return str(data["selected_model"])
    except (FileNotFoundError, ValueError, OSError):
        pass
    return _from_browser_config() or _from_toml() or DEFAULT_MODEL
