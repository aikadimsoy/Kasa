import os
import importlib
import tempfile
from fastapi.testclient import TestClient

def run() -> list[dict]:
    try:
        tmp = tempfile.mkdtemp()
        os.environ["KASA_VAULT_PATH"] = tmp
        import src.mcp_server.server as srv
        importlib.reload(srv)
        token = srv._BEARER_TOKEN
    except Exception as e:
        return [{"id": "FUZZ-SKIP", "category": "fuzz", "title": "Bootstrap Failure", "status": "SKIP", "severity": "info", "evidence": str(e), "remediation": ""}]
    
    FUZZ_PAYLOADS = [
        {},
        {"tool_calls": "not-a-list", "agent_id": "x"},
        {"tool_calls": [123], "agent_id": "x"},
        {"tool_calls": [{"tool_name": 123}], "agent_id": "x"},
        {"tool_calls": [{"tool_name": "x", "parameters": "not-a-dict"}], "agent_id": "x"},
        {"tool_calls": [{"tool_name": "profile_read", "parameters": {"scope": "user.name"}}], "agent_id": ""},
        {"tool_calls": [{"tool_name": "A"*100000, "parameters": {}}], "agent_id": "x"},
        {"tool_calls": [{"tool_name": "x", "parameters": {}}], "agent_id": "B"*100000},
        {"tool_calls": [{"tool_name": "; DROP TABLE profile;--", "parameters": {"scope": "../../etc/passwd"}}], "agent_id": "x"},
        {"tool_calls": [{"tool_name": "x" + chr(0) + "null", "parameters": {"k": chr(0x1F600) * 1000}}], "agent_id": "x"}
    ]
    
    results = []
    k = 0
    offending_statuses = []
    
    try:
        with TestClient(srv.app, raise_server_exceptions=False) as client:
            # Controller: gecerli-istek sayaci KALDIRILDI -> k'ye karisip "N > len(payloads)" off-by-one
            # uretiyordu (evidence yanlis sayiyordu). Artik k YALNIZ FUZZ_PAYLOADS'tan sayilir.
            # Fuzz with malicious payloads
            for payload in FUZZ_PAYLOADS:
                response = client.post("/v1/execute_tool", headers={"Authorization": "Bearer " + token}, json=payload)
                if response.status_code >= 500:
                    k += 1
                    offending_statuses.append(response.status_code)
            
            # Send malformed payload without authorization header
            response = client.post("/v1/execute_tool", json={})
            if response.status_code not in (401, 403):
                results.append({
                    "id": "FUZZ-NOAUTH",
                    "category": "fuzz",
                    "title": "Malformed unauthenticated request rejected",
                    "status": "FAIL" if response.status_code not in (401, 403) else "PASS",
                    "severity": "critical",
                    "evidence": f"Status code: {response.status_code}",
                    "remediation": "Reject unauthenticated requests before body parsing"
                })
            else:
                results.append({
                    "id": "FUZZ-NOAUTH",
                    "category": "fuzz",
                    "title": "Malformed unauthenticated request rejected",
                    "status": "PASS",
                    "severity": "critical",
                    "evidence": f"Status code: {response.status_code}",
                    "remediation": "Reject unauthenticated requests before body parsing"
                })
            
            # Final result for fuzzing robustness
            results.append({
                "id": "FUZZ-EXECUTE",
                "category": "fuzz",
                "title": "Malformed payload robustness (execute_tool)",
                "status": "PASS" if k == 0 else "FAIL",  # Controller splice: uretilen kod TERS'ti (k==0=cokme yok=PASS)
                "severity": "high",
                "evidence": f"{len(FUZZ_PAYLOADS)} malformed payloads sent, {k} caused 5xx" + (" with offending statuses: " + ', '.join(map(str, offending_statuses)) if k > 0 else ''),
                "remediation": "Return 4xx for malformed input; enforce request-model validation and size limits"
            })
    
    except Exception as e:
        results.append({
            "id": "FUZZ-SKIP",
            "category": "fuzz",
            "title": "Execution Failure",
            "status": "SKIP",
            "severity": "info",
            "evidence": str(e),
            "remediation": ""
        })
    
    finally:
        os.environ.pop("KASA_VAULT_PATH", None)

    return results
