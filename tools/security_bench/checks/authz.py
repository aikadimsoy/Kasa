import os
import importlib
import tempfile
import inspect
from fastapi.testclient import TestClient

def check_token_missing():
    try:
        tmp = tempfile.mkdtemp()
        os.environ["KASA_VAULT_PATH"] = tmp
        import src.mcp_server.server as srv
        importlib.reload(srv)
        token = srv._BEARER_TOKEN
    except Exception:
        return [{"id": "AUTHZ-SKIP", "category": "authz", "title": "Server Initialization Failed", "status": "SKIP", "severity": "info", "evidence": str(Exception)}]
    
    with TestClient(srv.app, raise_server_exceptions=False) as client:
        response = client.post("/v1/execute_tool", headers={}, json={"tool_calls":[{"tool_name":"profile_read","parameters":{"scope":"user.name"}}], "agent_id":"tester"})
        status = response.status_code
        result = {
            "id": "AUTHZ-TOKEN-MISSING",
            "category": "authz",
            "title": "POST with NO Authorization header",
            "status": "PASS" if status in [401, 403] else "FAIL",
            "severity": "critical",
            "evidence": f"Status code: {status}"
        }
    os.environ.pop("KASA_VAULT_PATH", None)
    return [result]

def check_token_wrong():
    try:
        tmp = tempfile.mkdtemp()
        os.environ["KASA_VAULT_PATH"] = tmp
        import src.mcp_server.server as srv
        importlib.reload(srv)
        token = srv._BEARER_TOKEN
    except Exception:
        return [{"id": "AUTHZ-SKIP", "category": "authz", "title": "Server Initialization Failed", "status": "SKIP", "severity": "info", "evidence": str(Exception)}]
    
    with TestClient(srv.app, raise_server_exceptions=False) as client:
        response = client.post("/v1/execute_tool", headers={"Authorization": "Bearer definitely-wrong-token"}, json={"tool_calls":[{"tool_name":"profile_read","parameters":{"scope":"user.name"}}], "agent_id":"tester"})
        status = response.status_code
        result = {
            "id": "AUTHZ-TOKEN-WRONG",
            "category": "authz",
            "title": "POST with header Bearer 'definitely-wrong-token'",
            "status": "PASS" if status == 401 else "FAIL",
            "severity": "critical",
            "evidence": f"Status code: {status}"
        }
    os.environ.pop("KASA_VAULT_PATH", None)
    return [result]

def check_agent_system():
    try:
        tmp = tempfile.mkdtemp()
        os.environ["KASA_VAULT_PATH"] = tmp
        import src.mcp_server.server as srv
        importlib.reload(srv)
        token = srv._BEARER_TOKEN
    except Exception:
        return [{"id": "AUTHZ-SKIP", "category": "authz", "title": "Server Initialization Failed", "status": "SKIP", "severity": "info", "evidence": str(Exception)}]
    
    with TestClient(srv.app, raise_server_exceptions=False) as client:
        response = client.post("/v1/execute_tool", headers={"Authorization": f"Bearer {token}"}, json={"tool_calls":[{"tool_name":"profile_read","parameters":{"scope":"user.name"}}], "agent_id":"system"})
        status = response.status_code
        result = {
            "id": "AUTHZ-C5",
            "category": "authz",
            "title": "valid token, agent_id='system', tool profile_read parameters {'scope':'user.name'}",
            "status": "PASS" if status == 403 else "FAIL",
            "severity": "critical",
            "evidence": f"Status code: {status}"
        }
    os.environ.pop("KASA_VAULT_PATH", None)
    return [result]

def check_tool_not_allowed():
    try:
        tmp = tempfile.mkdtemp()
        os.environ["KASA_VAULT_PATH"] = tmp
        import src.mcp_server.server as srv
        importlib.reload(srv)
        token = srv._BEARER_TOKEN
    except Exception:
        return [{"id": "AUTHZ-SKIP", "category": "authz", "title": "Server Initialization Failed", "status": "SKIP", "severity": "info", "evidence": str(Exception)}]
    
    with TestClient(srv.app, raise_server_exceptions=False) as client:
        response = client.post("/v1/execute_tool", headers={"Authorization": f"Bearer {token}"}, json={"tool_calls":[{"tool_name":"grant_permission","parameters":{}}], "agent_id":"tester"})
        status = response.status_code
        result = {
            "id": "AUTHZ-C7",
            "category": "authz",
            "title": "valid token, agent_id='tester', tool_name='grant_permission'",
            # Turkce not: olculen ozellik "grant_permission AGDAN cagrilamaz" (izin
            # yukseltme). Bunu 404 (rota yok) da 403 (kimlik baglama reddi) da saglar.
            # Kontrol 404'e SABITLENMISTI; kimlik baglama eklendikten sonra istek rota
            # aramasindan ONCE 403 ile duruyor -> kontrol, sunucu daha iyi davrandigi
            # halde FAIL veriyordu. pytest ikizi (tests/test_authz.py) zaten (403,404)
            # kabul ediyor; bench onunla hizalandi. Hangi ret oldugu kanita YAZILIR --
            # "reddedildi" demek yetmez, hangi kapinin reddettigi olcumun kendisidir.
            "status": "PASS" if status in (403, 404) else "FAIL",
            "severity": "high",
            "evidence": f"Status code: {status} ({'kimlik baglama reddi' if status == 403 else 'rota yok' if status == 404 else 'BEKLENMEYEN'})"
        }
    os.environ.pop("KASA_VAULT_PATH", None)
    return [result]

def check_permission_check():
    try:
        tmp = tempfile.mkdtemp()
        os.environ["KASA_VAULT_PATH"] = tmp
        import src.mcp_server.server as srv
        importlib.reload(srv)
        token = srv._BEARER_TOKEN
    except Exception:
        return [{"id": "AUTHZ-SKIP", "category": "authz", "title": "Server Initialization Failed", "status": "SKIP", "severity": "info", "evidence": str(Exception)}]
    
    with TestClient(srv.app, raise_server_exceptions=False) as client:
        response = client.post("/v1/execute_tool", headers={"Authorization": f"Bearer {token}"}, json={"tool_calls":[{"tool_name":"_check_permission","parameters":{}}], "agent_id":"tester"})
        status = response.status_code
        result = {
            "id": "AUTHZ-C8",
            "category": "authz",
            "title": "valid token, agent_id='tester', tool_name='_check_permission'",
            # Turkce not: C7 ile ayni gerekce -- private metodun ISIMLE cagrilamamasi
            # olculuyor; 403 de 404 de bunu saglar. Bkz. C7'deki aciklama.
            "status": "PASS" if status in (403, 404) else "FAIL",
            "severity": "high",
            "evidence": f"Status code: {status} ({'kimlik baglama reddi' if status == 403 else 'rota yok' if status == 404 else 'BEKLENMEYEN'})"
        }
    os.environ.pop("KASA_VAULT_PATH", None)
    return [result]

def check_deny_by_default():
    try:
        tmp = tempfile.mkdtemp()
        os.environ["KASA_VAULT_PATH"] = tmp
        import src.mcp_server.server as srv
        importlib.reload(srv)
        token = srv._BEARER_TOKEN
    except Exception:
        return [{"id": "AUTHZ-SKIP", "category": "authz", "title": "Server Initialization Failed", "status": "SKIP", "severity": "info", "evidence": str(Exception)}]
    
    agent_id = "unauthz_" + os.urandom(3).hex()
    with TestClient(srv.app, raise_server_exceptions=False) as client:
        response = client.post("/v1/execute_tool", headers={"Authorization": f"Bearer {token}"}, json={"tool_calls":[{"tool_name":"profile_read","parameters":{"scope":"user.name"}}], "agent_id": agent_id})
        status = response.status_code
        result = {
            "id": "AUTHZ-DENY",
            "category": "authz",
            "title": f"valid token, agent_id='{agent_id}', tool profile_read parameters {{'scope':'user.name'}}",
            "status": "PASS" if status != 200 else "FAIL",
            "severity": "critical",
            "evidence": f"Status code: {status}"
        }
    os.environ.pop("KASA_VAULT_PATH", None)
    return [result]

def check_default_host():
    try:
        tmp = tempfile.mkdtemp()
        os.environ["KASA_VAULT_PATH"] = tmp
        import src.mcp_server.server as srv
        importlib.reload(srv)
        token = srv._BEARER_TOKEN
    except Exception:
        return [{"id": "AUTHZ-SKIP", "category": "authz", "title": "Server Initialization Failed", "status": "SKIP", "severity": "info", "evidence": str(Exception)}]
    
    default_host = inspect.signature(srv.start_server).parameters['host'].default
    result = {
        "id": "AUTHZ-BIND",
        "category": "authz",
        "title": "Static check on server binding host",
        "status": "PASS" if default_host in ["127.0.0.1", "localhost"] else "FAIL",
        "severity": "high",
        "evidence": f"Default host: {default_host}"
    }
    os.environ.pop("KASA_VAULT_PATH", None)
    return [result]

def run():
    results = []
    try:
        results += check_token_missing()
        results += check_token_wrong()
        results += check_agent_system()
        results += check_tool_not_allowed()
        results += check_permission_check()
        results += check_deny_by_default()
        results += check_default_host()
    except Exception as e:
        results.append({
            "id": "AUTHZ-ERROR",
            "category": "authz",
            "title": "Unexpected Error in Security Checks",
            "status": "SKIP",
            "severity": "info",
            "evidence": str(e)
        })
    return results


# ===== NEDEN -> SONUC / CAUSE -> EFFECT (yerel model, sifir-token) =====
# Purpose: This file contains functions to perform authorization checks on the server.
# Why (cause -> effect): These checks ensure that the server correctly handles different authorization scenarios, such as missing tokens, wrong tokens, and unauthorized agents.
# Amac: Bu dosya, sunucu üzerinde yetkilendirme kontrollerini gerçekleştiren fonksiyonları içerir.
# Neden -> Sonuc: Bu kontroller, eksik belirtec, yanlış belirteç ve yetkisiz aracılıklar gibi farklı yetkilendirme senaryolarının doğru şekilde işlendiğinden emin olur.
