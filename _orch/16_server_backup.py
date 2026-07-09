# kasa/src/mcp_server/server.py

"""
MCP (Model Context Protocol) sunucusunu çalıştıran ana dosya.
Bu sunucu, localhost üzerinde bir HTTP sunucusu başlatır ve
ajanların Kasa (Vault) ile güvenli bir şekilde etkileşime girmesini
sağlayan araçları (tools) bir API üzerinden sunar.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ..vault.database import Vault
from .tools import VaultTools
from ..config import load_config, get_or_create_bearer_token
import pathlib

# -- Pydantic Modelleri (API şeması için) --

class ToolCall(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

class ExecuteToolRequest(BaseModel):
    tool_calls: List[ToolCall]
    agent_id: str = Field(..., description="Araçları çağıran ajanın kimliği.")

class ToolResult(BaseModel):
    tool_name: str
    result: Dict[str, Any]

class ExecuteToolResponse(BaseModel):
    results: List[ToolResult]

class SimpleToolRequest(BaseModel):
    tool: str
    agent_id: str = "browser_extension"
    params: Dict[str, Any] = {}

# -- Bağımlılıklar (Dependencies) --

# Kasa'yı global olarak başlat (uygulama ömrü boyunca tek bir tane)
# Gerçek bir uygulamada bu, daha sağlam bir konfigürasyon yönetimi gerektirir.
VAULT_PATH = os.environ.get("KASA_VAULT_PATH", "d:/kasa")
VAULT_INSTANCE = Vault(vault_path=VAULT_PATH)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama ömrü: vault bağla, şema kur, kapat."""
    from ..vault.schema import ALL_TABLES, ALL_INDEXES
    VAULT_INSTANCE.connect()
    conn = VAULT_INSTANCE.get_connection()
    for sql in ALL_TABLES + ALL_INDEXES:
        conn.execute(sql)
    conn.commit()
    yield
    VAULT_INSTANCE.close()

def get_vault() -> Vault:
    """FastAPI bağımlılığı: Vault nesnesini döndürür."""
    return VAULT_INSTANCE

# -- FastAPI Uygulaması --

app = FastAPI(
    title="Project KASA MCP Server",
    description="Ajanlar için yerel, güvenli hafıza kasası.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS ayarlarını yapılandır
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

# Bearer token authentication için gerekli olan dependency'yi tanımlayalım
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

_security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(_security)):
    if credentials.credentials != _BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Geçersiz token.")

# -- Endpoints --

@app.post("/v1/execute_tool", response_model=ExecuteToolResponse)
async def execute_tool(
    request: ExecuteToolRequest,
    vault: Vault = Depends(get_vault),
    _: None = Security(verify_token)  # Bearer token dependency
):
    """
    Bir veya daha fazla aracı (tool) çalıştırır.
    """
    tool_handler = VaultTools(vault, agent_id=request.agent_id)
    response_results = []

    for tool_call in request.tool_calls:
        tool_name = tool_call.tool_name
        params = tool_call.parameters

        if not hasattr(tool_handler, tool_name):
            raise HTTPException(
                status_code=404,
                detail=f"Araç bulunamadı: '{tool_name}'"
            )

        try:
            method = getattr(tool_handler, tool_name)
            # TODO: Asenkron araçları destekle
            result = method(**params)
            response_results.append(ToolResult(tool_name=tool_name, result=result))

        except TypeError as e:
            # Yanlış parametreler için
            raise HTTPException(
                status_code=422,
                detail=f"'{tool_name}' aracı için geçersiz parametreler: {e}"
            )

    return ExecuteToolResponse(results=response_results)

@app.post("/v1/ingest")
async def ingest(
    request: SimpleToolRequest,
    vault: Vault = Depends(get_vault),
    _: None = Security(verify_token),
):
    """Basit tek-araç endpoint'i (browser extension + Native Messaging icin)."""
    tool_handler = VaultTools(vault, agent_id=request.agent_id)
    if not hasattr(tool_handler, request.tool):
        raise HTTPException(status_code=404, detail=f"Araç bulunamadı: '{request.tool}'")
    try:
        method = getattr(tool_handler, request.tool)
        result = method(**request.params)
        return {"status": "success", "result": result}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def health_check():
    """Health check — auth gerektirmez."""
    return {"status": "ok", "version": "0.2.0"}


def start_server(host: str = "127.0.0.1", port: int = 8000):
    print(f"[KASA] MCP sunucusu baslatiliyor: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()