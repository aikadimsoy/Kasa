# kasa/src/mcp_adapter/proxy.py

"""
MCP adapter proxy core — NO `mcp` SDK import here, so this logic is unit-testable under
any interpreter. __main__.py wraps these functions with FastMCP tool decorators.

Security invariants enforced here:
  - loopback-only server URL (air-gap),
  - reserved agent id "system" refused locally (server refuses too; defense in depth),
  - every call goes through the server's full authz stack (bearer + allow-list + scopes).

Turkce not: MCP adaptorunun cekirdegi. `mcp` SDK'sini IMPORT etmez, boylece her yorumlayicida
birim-test edilebilir; __main__.py bu fonksiyonlari FastMCP ile sarar. Guvenlik degismezleri:
yalniz loopback (hava-boslugu), "system" kimligi yerelde reddedilir, ve HER cagri sunucunun
tam yetki yiginindan (bearer + allow-list + kapsam) gecer.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from src.config import load_config

_TIMEOUT = 30  # saniye; yerel cagri icin bol

# Loopback ana-adlari. IPv6 loopback (::1) dahil; digerleri reddedilir.
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _is_loopback_url(url: str) -> bool:
    """True yalnizca URL http/https ve ANA-ADI tam olarak bir loopback ise.

    Turkce not (guvenlik olcumu): eskiden `url.startswith("http://127.0.0.1")` idi ve
    `http://127.0.0.1.evil.example` ile `http://127.0.0.1@evil.example` bu METINSEL
    kontrolden GECIYORDU (biri alt-alan, digeri userinfo hilesi) -> air-gap iddiasi
    yaniltici. Cozum: URL'yi AYRISTIR ve yalnizca `hostname`i (userinfo/port haric,
    ayristiricinin cozdugu gercek ana-ad) tam-eslesme ile denetle.
    """
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    return (p.hostname or "").lower() in _LOOPBACK_HOSTS


def build_settings() -> dict:
    """Resolve bearer/base_url/agent_id from config+env. Raises ValueError on violations."""
    cfg = load_config()
    bearer = cfg.get("server", {}).get("bearer_token", "")
    host = cfg.get("server", {}).get("host", "127.0.0.1")
    port = int(cfg.get("server", {}).get("port", 8000))
    # Air-gap: adaptor yalniz loopback'e konusur; config baska sey dese bile zorlanir.
    if host not in ("127.0.0.1", "localhost"):
        host = "127.0.0.1"
    base_url = os.environ.get("KASA_SERVER_URL") or f"http://{host}:{port}"
    if not _is_loopback_url(base_url):
        raise ValueError("only loopback server URLs are allowed (air-gap)")
    agent_id = os.environ.get("KASA_MCP_AGENT_ID", "mcp_client")
    if agent_id == "system":
        raise ValueError("agent id 'system' is reserved and refused")
    return {"bearer": bearer, "base_url": base_url, "agent_id": agent_id}


def execute(settings: dict, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """Proxy one tool call through the server's full authz stack. Returns the tool result
    dict, or raises ValueError with the server's error detail (MCP client sees the text)."""
    body = json.dumps({
        "tool_calls": [{"tool_name": tool_name, "parameters": parameters}],
        "agent_id": settings["agent_id"],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{settings['base_url']}/v1/execute_tool",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings['bearer']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail", str(e))
        except Exception:
            detail = str(e)
        raise ValueError(f"KASA server rejected the call (HTTP {e.code}): {detail}") from None
    except urllib.error.URLError as e:
        raise ValueError(
            f"KASA server unreachable at {settings['base_url']} — is KASA running? ({e.reason})"
        ) from None
    results = payload.get("results") or []
    if not results:
        raise ValueError("KASA server returned no result.")
    return results[0].get("result", {})
