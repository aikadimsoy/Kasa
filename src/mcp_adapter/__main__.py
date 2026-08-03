# kasa/src/mcp_adapter/__main__.py

"""
KASA MCP stdio adapter — bridges MCP clients (Claude Code, Goose, Cline) to the
running KASA REST server. Proxy core lives in proxy.py (SDK-free, unit-tested);
this module only wires FastMCP tool schemas around it.

Security model (unchanged, by design): this process holds NO privileged path into the
vault. Every tools/call is proxied to ``POST /v1/execute_tool`` with the bearer from
kasa.toml, so ALL existing gates apply: bearer auth, PUBLIC_TOOLS allow-list,
reserved-agent-id block, per-scope deny-by-default permissions, audit chain.

Run:  py -3.12 -m src.mcp_adapter
Wire: claude mcp add kasa -- py -3.12 -m src.mcp_adapter

Copyright note: depends only on the official `mcp` SDK (MIT). All code here is original.

Turkce not: KASA MCP stdio adaptoru — MCP istemcilerini (Claude Code, Goose, Cline) calisan
KASA REST sunucusuna baglar. Bu surec vault'a AYRICALIKLI yol TUTMAZ; her cagri kasa.toml'daki
bearer ile POST /v1/execute_tool'a proxy'lenir. Boylece tum kapilar (bearer, PUBLIC_TOOLS
allow-list, reserved-id blogu, kapsam varsayilan-red, audit zinciri) oldugu gibi gecerli kalir.
"""

from __future__ import annotations

import os
import sys
from typing import Any

# Repo kokunu sys.path'e ekle (farkli cwd'den calistirilsa da src cozulsun).
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from mcp.server.fastmcp import FastMCP  # noqa: E402  (MIT-licensed official SDK)

from src.mcp_adapter import proxy  # noqa: E402

try:
    _SETTINGS = proxy.build_settings()
except ValueError as e:
    raise SystemExit(f"KASA MCP adapter: {e}")


def _execute(tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return proxy.execute(_SETTINGS, tool_name, parameters)


mcp = FastMCP(
    "kasa",
    instructions=(
        "KASA is a local-first personal memory vault. All calls are authorized and audited "
        "by the KASA server (deny-by-default permissions per agent). Reads are redacted."
    ),
)


# --- PUBLIC_TOOLS yuzeyi (sunucudaki allow-list ile birebir; grant_permission YOK) ---

@mcp.tool()
def event_ingest(source: str, type: str, content: dict, ttl_days: int = 30) -> dict:
    """Store an event in the vault (content is redacted+encrypted server-side).
    Requires the 'events:write' permission for this agent."""
    return _execute("event_ingest", {
        "source": source, "type": type, "content": content, "ttl_days": ttl_days})


@mcp.tool()
def profile_read(scope: str) -> dict:
    """Read profile keys (supports 'user.*' wildcard). Requires 'profile:read:<scope>'."""
    return _execute("profile_read", {"scope": scope})


@mcp.tool()
def profile_write(key: str, value: Any, provenance: list[int]) -> dict:
    """Write a profile fact with provenance event ids. Requires 'profile:write'."""
    return _execute("profile_write", {"key": key, "value": value, "provenance": provenance})


@mcp.tool()
def forget(topic: str) -> dict:
    """Delete profile keys and matching events for a topic (tombstoned).
    Requires 'admin:forget'."""
    return _execute("forget", {"topic": topic})


@mcp.tool()
def audit_read(start_index: int = 0, count: int = 100) -> dict:
    """Read the tamper-evident audit chain. Requires 'audit:read'."""
    return _execute("audit_read", {"start_index": start_index, "count": count})


@mcp.tool()
def prune_expired_events() -> dict:
    """Delete expired, already-distilled events. Requires 'admin:prune'."""
    return _execute("prune_expired_events", {})


if __name__ == "__main__":
    mcp.run()  # stdio transport (varsayilan)
