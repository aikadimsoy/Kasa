# kasa/src/agent/gate.py

"""
Deterministic gate for the agent bridge — the security boundary between the selected
local model and KASA. HAND-WRITTEN (security carve-out); local models do not edit this.

Principles (project law):
  - AI is an ADVISOR; every tool call the model emits passes this gate. The gate's verdict
    is final and rule-based — never model-based.
  - Name allow-list is a NAMESPACE gate, not a content gate (red-team lesson): therefore
    every string argument also passes a CONTENT gate (credential-phrase denylist).
  - The tool surface is READ-ONLY masked dashboard functions. `kasa_note` (write) is
    designed in but ships DISABLED (allow_notes=False) and its permission is not seeded.
  - Bounded everything: iterations, wall clock, argument sizes, result sizes, history.
"""

from __future__ import annotations

import re
from typing import Any

from ..vault.redact import CREDENTIAL_DENY

# --- Sinirlar (harness bunlari uygular; testler sabitligini korur) ---
MAX_ITERATIONS = 5          # sohbet basina en fazla arac-cagrisi turu
CALL_TIMEOUT_S = 120        # tek model cagrisi
TOTAL_TIMEOUT_S = 300       # tum sohbet dongusu (duvar saati)
MAX_RESULT_CHARS = 8000     # modele geri beslenen arac sonucu (kirpilir)
MAX_MESSAGE_CHARS = 4000    # kullanici mesaji
MAX_HISTORY_MSGS = 20       # gecmis mesaj adedi
MAX_REPLY_CHARS = 16000     # modelin nihai cevabi (kirpilir)
MAX_NOTE_CHARS = 2000       # kasa_note metni (bayrak kapaliyken de tanimli)
MIN_RACE_MODELS = 2         # Yaris Modu: en az 2 model yan yana
MAX_RACE_MODELS = 4         # Yaris Modu: en fazla 4 (yerel GPU butcesi)

# Ajanin sunucu-tarafi sabit kimligi (asla istemciden alinmaz).
PANEL_AGENT_ID = "panel_agent"

_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9._:\-]{1,100}$")

# --- Arac kayit defteri ---
# handler'lar harness'ta baglanir; burada YALNIZ sema + kural. "readonly" bilgi amaclidir:
# yuzeydeki tek yazici kasa_note'tur ve allow_notes bayragina kilitlidir.
TOOLS: dict[str, dict] = {
    "kasa_stats": {
        "description": "Vault summary statistics (aggregate only; no raw content).",
        "params": {},
        "readonly": True,
    },
    "kasa_recent_events": {
        "description": "Recent events, masked structural metadata only (no content field).",
        "params": {
            "limit": {"type": int, "min": 1, "max": 100, "default": 20},
        },
        "readonly": True,
    },
    "kasa_profile": {
        "description": "Persistent profile entries, values masked through redaction.",
        "params": {
            "limit": {"type": int, "min": 1, "max": 200, "default": 50},
        },
        "readonly": True,
    },
    # Yazici: bayrak kapali sevk edilir (owner karari, 2026-07-10). Izin de seed edilmez.
    "kasa_note": {
        "description": "Save a short note to the vault (owner-gated; disabled by default).",
        "params": {
            "text": {"type": str, "maxlen": MAX_NOTE_CHARS, "required": True},
        },
        "readonly": False,
    },
}


def _content_gate(value: str) -> str | None:
    """Icerik kapisi: kredensiyel-ifade denylist'i (ad-listesi != icerik kapisi).
    Ihlal metni doner (red sebebi), temizse None."""
    low = value.lower()
    for phrase in CREDENTIAL_DENY:
        if phrase in low:
            return f"content gate: credential-like phrase ({phrase!r})"
    return None


def validate_call(tool_name: str, args: Any, allow_notes: bool = False) -> tuple[bool, Any]:
    """Modelin urettigi tek bir arac cagrisini dogrular.
    Donen: (True, normalize_edilmis_args) | (False, red_sebebi:str)."""
    spec = TOOLS.get(tool_name)
    if spec is None:
        return False, f"unknown tool {tool_name!r}"
    if not spec["readonly"] and not allow_notes:
        return False, f"tool {tool_name!r} is disabled (read-only mode)"
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return False, "arguments must be an object"

    params = spec["params"]
    unknown = set(args) - set(params)
    if unknown:
        return False, f"unknown argument(s): {sorted(unknown)}"

    norm: dict[str, Any] = {}
    for name, rule in params.items():
        if name not in args:
            if rule.get("required"):
                return False, f"missing required argument {name!r}"
            if "default" in rule:
                norm[name] = rule["default"]
            continue
        val = args[name]
        typ = rule["type"]
        if typ is int:
            # bool, int'in alt-tipi — acikca reddet.
            if isinstance(val, bool) or not isinstance(val, int):
                return False, f"argument {name!r} must be an integer"
            if not (rule["min"] <= val <= rule["max"]):
                return False, f"argument {name!r} out of range [{rule['min']}..{rule['max']}]"
            norm[name] = val
        elif typ is str:
            if not isinstance(val, str):
                return False, f"argument {name!r} must be a string"
            if len(val) > rule["maxlen"]:
                return False, f"argument {name!r} exceeds {rule['maxlen']} chars"
            hit = _content_gate(val)
            if hit:
                return False, f"argument {name!r} rejected: {hit}"
            norm[name] = val
        else:  # pragma: no cover — kayit defteri hatasi
            return False, f"unsupported parameter type for {name!r}"
    return True, norm


def validate_model_name(name: Any, installed: set[str]) -> tuple[bool, str]:
    """Model adi: bicim regex'i + kurulu-model allow-list uyeligi."""
    if not isinstance(name, str) or not _MODEL_NAME_RE.match(name or ""):
        return False, "invalid model name format"
    if name not in installed:
        return False, f"model {name!r} is not installed"
    return True, ""


def validate_race_models(models: Any, installed: set[str]) -> tuple[bool, object]:
    """Yaris Modu model listesi: 2..MAX_RACE_MODELS benzersiz ad, her biri kurulu + bicimli.
    Doner: (True, normalize_edilmis_liste) | (False, red_sebebi:str). Sira korunur, tekil."""
    if not isinstance(models, list):
        return False, "models must be a list"
    # Sirali tekillestir.
    seen: list[str] = []
    for m in models:
        if m not in seen:
            seen.append(m)
    if not (MIN_RACE_MODELS <= len(seen) <= MAX_RACE_MODELS):
        return False, f"select between {MIN_RACE_MODELS} and {MAX_RACE_MODELS} distinct models"
    for name in seen:
        ok, reason = validate_model_name(name, installed)
        if not ok:
            return False, f"{name!r}: {reason}"
    return True, seen


def validate_message(message: Any) -> tuple[bool, str]:
    """Kullanici mesaji: tip + bos-olmama + uzunluk. (Icerik kapisi arac ARG'larina uygulanir;
    kullanicinin kendi sorusu modele gider, vault'a degil.)"""
    if not isinstance(message, str):
        return False, "message must be a string"
    if not message.strip():
        return False, "message is empty"
    if len(message) > MAX_MESSAGE_CHARS:
        return False, f"message exceeds {MAX_MESSAGE_CHARS} chars"
    return True, ""


def validate_history(history: Any) -> tuple[bool, str]:
    """Sohbet gecmisi: liste + rol/icerik semasi + adet/uzunluk sinirlari."""
    if history is None:
        return True, ""
    if not isinstance(history, list):
        return False, "history must be a list"
    if len(history) > MAX_HISTORY_MSGS:
        return False, f"history exceeds {MAX_HISTORY_MSGS} messages"
    for i, item in enumerate(history):
        if not isinstance(item, dict):
            return False, f"history[{i}] must be an object"
        if item.get("role") not in ("user", "assistant"):
            return False, f"history[{i}].role must be 'user' or 'assistant'"
        content = item.get("content")
        if not isinstance(content, str) or len(content) > MAX_MESSAGE_CHARS:
            return False, f"history[{i}].content invalid or too long"
    return True, ""


def chat_tool_schemas(allow_notes: bool = False) -> list[dict]:
    """Yerel servisin /api/chat 'tools' parametresi icin sema listesi (OpenAI-bicimi).
    Kapali yazicilar semaya HIC girmez (model gormez)."""
    out: list[dict] = []
    for name, spec in TOOLS.items():
        if not spec["readonly"] and not allow_notes:
            continue
        properties: dict[str, dict] = {}
        required: list[str] = []
        for pname, rule in spec["params"].items():
            if rule["type"] is int:
                properties[pname] = {
                    "type": "integer",
                    "minimum": rule["min"], "maximum": rule["max"],
                    "description": f"integer in [{rule['min']}..{rule['max']}]",
                }
            else:
                properties[pname] = {"type": "string", "maxLength": rule["maxlen"]}
            if rule.get("required"):
                required.append(pname)
        out.append({
            "type": "function",
            "function": {
                "name": name,
                "description": spec["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return out
