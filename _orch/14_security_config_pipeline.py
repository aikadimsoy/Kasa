"""
Pipeline 14 — Güvenlik Düzeltmesi + Config Modülü
deepseek taslak → qwen review → dosyalara yaz

Hedef:
  src/config.py          — config.toml yükle, bearer token üret
  src/mcp_server/server.py — CORS fix + Bearer token doğrulama
  kasa.toml.example      — proje kökünde örnek config
"""
import json, pathlib, urllib.request

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
KASA     = pathlib.Path("d:/kasa")

def call_model(model, prompt, label, max_tokens=5000):
    print(f"\n[ORCH] {label} ({model})...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": 0.2, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(
        OLLAMA, data=payload,
        headers={"Content-Type": "application/json"}
    )
    buf = []
    with urllib.request.urlopen(req, timeout=300) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line: continue
            try:
                obj = json.loads(line)
                tok = obj.get("response", "")
                buf.append(tok); print(tok, end="", flush=True)
                if obj.get("done"): break
            except: continue
    print(); return "".join(buf)

def extract_python(text):
    if "```python" in text:
        s = text.find("```python") + 9
        return text[s:text.find("```", s)].strip()
    if "```" in text:
        s = text.find("```") + 3
        return text[s:text.find("```", s)].strip()
    return text.strip()

def syntax_ok(path):
    import subprocess, sys
    r = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open(r'{path}').read()); print('OK')"],
        capture_output=True, text=True
    )
    return "OK" in r.stdout, r.stderr

# ═══════════════════════════════════════════════════════════════
# GÖREV 1 — src/config.py
# ═══════════════════════════════════════════════════════════════

CONFIG_DRAFT = """
You are an expert Python developer. Write a complete `config.py` module for Project KASA.

## Purpose
Load configuration from `kasa.toml` (project root). If the file does not exist, use
sensible defaults and create it. On first run, generate a random Bearer token and save it.

## Requirements

### `load_config(config_path: Path = None) -> dict`
- Looks for `kasa.toml` in: config_path → KASA_CONFIG env var → `~/.kasa/kasa.toml` → `./kasa.toml`
- If not found: create it with DEFAULT_CONFIG (see below)
- Returns merged dict (file values override defaults)
- Uses `tomllib` (Python 3.11+) with fallback to `tomli` package, with fallback to manual parse

### `get_or_create_bearer_token(config: dict, config_path: Path) -> str`
- If `config["server"]["bearer_token"]` is empty/missing: generate `secrets.token_urlsafe(32)`
- Write the token back into kasa.toml under [server] bearer_token = "..."
- Return the token

### `DEFAULT_CONFIG`
```python
DEFAULT_CONFIG = {
    "server": {
        "host": "127.0.0.1",
        "port": 8000,
        "bearer_token": "",
        "allowed_origins": ["http://localhost", "http://127.0.0.1", "null"],
    },
    "vault": {
        "path": "~/.kasa/vault",
        "ttl_days": 30,
    },
    "distill": {
        "model": "qwen2.5:7b",
        "ollama_url": "http://localhost:11434",
        "schedule_hour": 2,
    },
}
```

### TOML fallback parser (if neither tomllib nor tomli available)
Write a minimal `_parse_toml_simple(text: str) -> dict` that handles:
- `[section]` headers
- `key = "value"` string values
- `key = 123` int values
- `key = ["a", "b"]` simple string arrays
- Comments (#)
This is a last-resort fallback only.

### `write_toml(data: dict, path: Path) -> None`
Writes a dict to TOML format (simple, no nested beyond 1 level).

## Imports allowed
`pathlib`, `os`, `secrets`, `json`, `re`, `time`
Try: `import tomllib` (3.11+) then `import tomli as tomllib` then use fallback.

## Output
ONLY the complete Python code. No markdown, no explanations. Start with imports.
""".strip()

raw1 = call_model(DRAFTER, CONFIG_DRAFT, "TASLAK — config.py")

REVIEW_CONFIG = f"""
Review this Python `config.py` module. Fix any issues:

```python
{raw1[:4000]}
```

Checks:
1. `tomllib` import must try built-in first, then `tomli`, then fallback — fix if not
2. `get_or_create_bearer_token` must write token back to kasa.toml — fix if missing
3. `load_config` must handle missing file gracefully — fix if it raises
4. `DEFAULT_CONFIG` must have all required keys — fix if missing
5. No external deps except optional `tomli`

Return ONLY corrected Python code. No markdown.
""".strip()

raw1r = call_model(REVIEWER, REVIEW_CONFIG, "REVIEW — config.py")
config_code = extract_python(raw1r)

config_path = KASA / "src" / "config.py"
config_path.write_text(config_code, encoding="utf-8")
ok, err = syntax_ok(config_path)
print(f"[ORCH] config.py → {'✅ SYNTAX OK' if ok else '⚠️  HATA: ' + err}")

# ═══════════════════════════════════════════════════════════════
# GÖREV 2 — src/mcp_server/server.py (güvenlik düzeltmesi)
# ═══════════════════════════════════════════════════════════════

server_current = (KASA / "src" / "mcp_server" / "server.py").read_text(encoding="utf-8")

SERVER_DRAFT = f"""
You are a FastAPI security expert. Rewrite this KASA MCP server with two security fixes.

## Current server.py:
```python
{server_current}
```

## Fix 1 — CORS: replace allow_origins=["*"]
New logic:
```python
from ..config import load_config, get_or_create_bearer_token
import pathlib
_CONFIG_PATH = pathlib.Path(__file__).parent.parent.parent / "kasa.toml"
_cfg = load_config(_CONFIG_PATH)
_BEARER_TOKEN = get_or_create_bearer_token(_cfg, _CONFIG_PATH)
_ALLOWED_ORIGINS = _cfg["server"]["allowed_origins"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

## Fix 2 — Bearer token authentication FastAPI dependency:
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

_security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(_security)):
    if credentials.credentials != _BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Geçersiz token.")
```

Apply `verify_token` as a dependency to ALL endpoints EXCEPT GET `/` (health check).

## Rules:
- Keep ALL existing logic (lifespan, execute_tool, ingest, etc.) intact
- Only add the security layer, do not remove or refactor other code
- `VAULT_PATH` still reads from `os.environ.get("KASA_VAULT_PATH")` OR falls back to `_cfg["vault"]["path"]`

Return ONLY the complete updated server.py code. No markdown.
""".strip()

raw2 = call_model(DRAFTER, SERVER_DRAFT, "TASLAK — server.py güvenlik")

REVIEW_SERVER = f"""
Review this updated FastAPI server.py. Check:

```python
{raw2[:4000]}
```

1. `allow_origins=["*"]` must NOT appear — fix if it does
2. Bearer token dependency must be applied to `/v1/execute_tool` and `/v1/ingest` — fix if missing
3. GET `/` must NOT require auth (health check) — fix if it does
4. `load_config` and `get_or_create_bearer_token` must be imported from `..config` — fix if wrong
5. All existing endpoint logic must be preserved

Return ONLY corrected server.py code. No markdown.
""".strip()

raw2r = call_model(REVIEWER, REVIEW_SERVER, "REVIEW — server.py")
server_code = extract_python(raw2r)

server_path = KASA / "src" / "mcp_server" / "server.py"
(KASA / "_orch" / "14_server_backup.py").write_text(
    server_current, encoding="utf-8"
)
server_path.write_text(server_code, encoding="utf-8")
ok2, err2 = syntax_ok(server_path)
print(f"[ORCH] server.py → {'✅ SYNTAX OK' if ok2 else '⚠️  HATA: ' + err2}")

# ═══════════════════════════════════════════════════════════════
# GÖREV 3 — kasa.toml.example
# ═══════════════════════════════════════════════════════════════

toml_example = """\
# kasa.toml — Project KASA Configuration
# Copy to kasa.toml and customize. Bearer token is auto-generated on first run.

[server]
host = "127.0.0.1"
port = 8000
bearer_token = ""   # auto-filled on first run
allowed_origins = ["http://localhost", "http://127.0.0.1", "null"]

[vault]
path = "~/.kasa/vault"   # use absolute path or ~ for home dir
ttl_days = 30

[distill]
model = "qwen2.5:7b"
ollama_url = "http://localhost:11434"
schedule_hour = 2        # 02:00 local time
"""

(KASA / "kasa.toml.example").write_text(toml_example, encoding="utf-8")
print("[ORCH] ✅ kasa.toml.example yazıldı")

# ═══════════════════════════════════════════════════════════════
print("\n[ORCH] Pipeline 14 tamamlandı.")
print(f"  config.py   → {config_path}")
print(f"  server.py   → {server_path}")
print(f"  backup      → d:/kasa/_orch/14_server_backup.py")
print(f"  örnek config → {KASA}/kasa.toml.example")
print("\nSONRAKİ ADIM: testleri çalıştır → python -m pytest tests/")
