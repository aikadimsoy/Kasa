import os
import json
import urllib.request
from urllib.error import HTTPError
import re

BASE = "http://127.0.0.1:8000"

def read_token():
    with open("d:/kasa/kasa.toml", 'r') as file:
        for line in file:
            match = re.search(r'bearer_token\s*=\s*"([^"]+)"', line)
            if match:
                return match.group(1)
    raise ValueError("Token not found")

def post(path, body, headers):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data, headers)
    try:
        with urllib.request.urlopen(req) as response:
            return (response.getcode(), response.read().decode('utf-8'))
    except HTTPError as e:
        return (e.code, e.read().decode('utf-8'))

TOKEN = read_token()
AUTH = {"Authorization": f"Bearer {TOKEN}", "Content-Type":"application/json"}

def check_health():
    url = f"{BASE}/"
    req = urllib.request.Request(url, headers={})
    try:
        with urllib.request.urlopen(req) as response:
            return (response.getcode(), response.read().decode('utf-8'))
    except HTTPError as e:
        return (e.code, e.read().decode('utf-8'))

def write_results(results):
    with open("probe_results.json", 'w') as file:
        json.dump(results, file)

results = []

# C1 health check
status_code, response = check_health()
result = "SECURE" if status_code == 200 else "VULNERABLE"
results.append({"check": "C1", "verdict": result, "status": status_code, "detail": response})
print(f"[{'SECURE' if status_code == 200 else 'VULN'}] C1 health -> {response}")

# C2 no_token check
try:
    status_code, response = post("/v1/ingest", {"tool": "event_ingest", "agent_id": "system", "params": {"source": "probe", "type": "t", "content": {"a": 1}}}, {})
    result = "SECURE" if status_code in [401, 403] else "VULNERABLE"
    results.append({"check": "C2", "verdict": result, "status": status_code, "detail": response})
    print(f"[{'SECURE' if status_code in [401, 403] else 'VULN'}] C2 no_token -> {response}")
except HTTPError as e:
    results.append({"check": "C2", "verdict": "VULNERABLE" if e.code == 401 else "SECURE", "status": e.code, "detail": str(e.read())})
    print(f"[{'SECURE' if e.code == 401 else 'VULN'}] C2 no_token -> {str(e.read())}")

# C3 wrong_token check
try:
    status_code, response = post("/v1/ingest", {"tool": "event_ingest", "agent_id": "system", "params": {"source": "probe", "type": "t", "content": {"a": 1}}}, {"Authorization": "Bearer deadbeef"})
    result = "SECURE" if status_code == 401 else "VULNERABLE"
    results.append({"check": "C3", "verdict": result, "status": status_code, "detail": response})
    print(f"[{'SECURE' if status_code == 401 else 'VULN'}] C3 wrong_token -> {response}")
except HTTPError as e:
    results.append({"check": "C3", "verdict": "VULNERABLE" if e.code == 401 else "SECURE", "status": e.code, "detail": str(e.read())})
    print(f"[{'SECURE' if e.code == 401 else 'VULN'}] C3 wrong_token -> {str(e.read())}")

# C4 baseline_write check
try:
    status_code, response = post("/v1/ingest", {"tool": "event_ingest", "agent_id": "system", "params": {"source": "probe", "type": "t", "content": {"a": 1}}}, AUTH)
    result = "SECURE" if status_code == 200 else "VULNERABLE"
    results.append({"check": "C4", "verdict": result, "status": status_code, "detail": response})
    print(f"[{'SECURE' if status_code == 200 else 'VULN'}] C4 baseline_write -> {response}")
except HTTPError as e:
    results.append({"check": "C4", "verdict": "VULNERABLE" if e.code >= 400 else "SECURE", "status": e.code, "detail": str(e.read())})
    print(f"[{'SECURE' if status_code == 200 else 'VULN'}] C4 baseline_write -> {str(e.read())}")

# C5 system_privilege_bypass check
try:
    response = post("/v1/execute_tool", {"agent_id": "system", "tool_calls": [{"tool_name": "profile_write", "parameters": {"key": "pwn.sys", "value": "x", "provenance": []}}]}, AUTH)
    result = "VULNERABLE" if response[0] == 200 and 'success' in response[1] else "SECURE"
    results.append({"check": "C5", "verdict": result, "status": response[0], "detail": response[1]})
    print(f"[{'SECURE' if response[0] != 200 or 'success' not in response[1] else 'VULN'}] C5 system_privilege_bypass -> {response[1]}")
except HTTPError as e:
    results.append({"check": "C5", "verdict": "SECURE" if e.code >= 400 else "VULNERABLE", "status": e.code, "detail": str(e.read())})
    print(f"[{'SECURE' if e.code >= 400 else 'VULN'}] C5 system_privilege_bypass -> {str(e.read())}")

# C6 deny_by_default check
try:
    response = post("/v1/execute_tool", {"agent_id": "attacker_random", "tool_calls": [{"tool_name": "profile_write", "parameters": {"key": "pwn.a", "value": "x", "provenance": []}}]}, AUTH)
    result = "SECURE" if response[0] not in [200, 201] else "VULNERABLE"
    results.append({"check": "C6", "verdict": result, "status": response[0], "detail": response[1]})
    print(f"[{'SECURE' if response[0] not in [200, 201] else 'VULN'}] C6 deny_by_default -> {response[1]}")
except HTTPError as e:
    results.append({"check": "C6", "verdict": "SECURE" if e.code >= 400 else "VULNERABLE", "status": e.code, "detail": str(e.read())})
    print(f"[{'SECURE' if e.code >= 400 else 'VULN'}] C6 deny_by_default -> {str(e.read())}")

def check_server_crash():
    # Saldiridan sonra sunucu hala saglikli mi?
    st, _ = check_health()
    return st == 200

# C7 grant_permission_escalation: once self-grant dene, SONRA ayni agent ile yaz -> gercekten yukseldi mi?
post("/v1/execute_tool", {"agent_id": "attacker_random",
     "tool_calls": [{"tool_name": "grant_permission", "parameters": {"scope": "profile:write"}}]}, AUTH)
st, resp = post("/v1/execute_tool", {"agent_id": "attacker_random",
     "tool_calls": [{"tool_name": "profile_write", "parameters": {"key": "pwn.esc", "value": "x", "provenance": []}}]}, AUTH)
vuln = (st == 200 and 'success' in resp)
results.append({"check": "C7", "verdict": "VULNERABLE" if vuln else "SECURE", "status": st, "detail": resp[:300]})
print(f"[{'VULN' if vuln else 'SECURE'}] C7 grant_permission_escalation -> {resp[:140]}")

# C8 private_method_exposure: hasattr allow-list'siz -> private metod cagirilabilir mi?
st, resp = post("/v1/execute_tool", {"agent_id": "attacker_random",
     "tool_calls": [{"tool_name": "_check_permission", "parameters": {"scope": "x"}}]}, AUTH)
secure = (st == 404)  # 404 = metod ifsa edilmedi (guvenli); baska her sey = private metoda erisildi
results.append({"check": "C8", "verdict": "SECURE" if secure else "VULNERABLE", "status": st, "detail": resp[:300]})
print(f"[{'SECURE' if secure else 'VULN'}] C8 private_method_exposure -> {st} {resp[:100]}")

# C9 cors_reflection: Origin: evil gonder, ACAO yansitiliyor mu?
acao = None
try:
    req = urllib.request.Request(f"{BASE}/", headers={"Origin": "https://evil.example"})
    with urllib.request.urlopen(req) as r:
        acao = r.getheader("Access-Control-Allow-Origin")
except HTTPError as e:
    acao = e.headers.get("Access-Control-Allow-Origin")
secure = (acao is None) or ("evil.example" not in (acao or ""))
results.append({"check": "C9", "verdict": "SECURE" if secure else "VULNERABLE", "status": 200, "detail": str(acao)})
print(f"[{'SECURE' if secure else 'VULN'}] C9 cors_reflection -> ACAO={acao}")

# C10 sql_injection_content: parametrize mi? (payload gonder, sunucu ayakta mi?)
st, resp = post("/v1/ingest", {"tool": "event_ingest", "agent_id": "system",
     "params": {"source": "probe", "type": "t", "content": {"x": "'); DROP TABLE events;--"}}}, AUTH)
healthy = check_server_crash()
results.append({"check": "C10", "verdict": "SECURE" if healthy else "VULNERABLE", "status": st,
                "detail": ("healthy" if healthy else "CRASHED") + f" resp={resp[:120]}"})
print(f"[{'SECURE' if healthy else 'VULN'}] C10 sql_injection_content -> {'healthy' if healthy else 'CRASHED'}")

# C11 oversized_source: 5000 karakter kaynak -> ValueError yonetiliyor mu, sunucu ayakta mi?
st, resp = post("/v1/ingest", {"tool": "event_ingest", "agent_id": "system",
     "params": {"source": "A" * 5000, "type": "t", "content": {"a": 1}}}, AUTH)
healthy = check_server_crash()
results.append({"check": "C11", "verdict": "SECURE" if healthy else "VULNERABLE", "status": st,
                "detail": ("healthy" if healthy else "CRASHED") + f" resp={resp[:120]}"})
print(f"[{'SECURE' if healthy else 'VULN'}] C11 oversized_source -> {'healthy' if healthy else 'CRASHED'} (status {st})")

vulns = [r for r in results if r["verdict"] == "VULNERABLE"]
print(f"\n=== OZET: {len(vulns)}/{len(results)} VULNERABLE -> " + ", ".join(r["check"] for r in vulns))
write_results(results)
