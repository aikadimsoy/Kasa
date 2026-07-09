# -*- coding: utf-8 -*-
"""
KASA — MCP authz (C5/C7/C8) regresyon testi ureticisi (sifir-token)
deepseek taslak -> qwen inceleme -> py_compile -> d:/kasa/tests/test_authz.py
Testler GUVENLI son-durumu iddia eder: fix'ten ONCE FAIL, fix'ten SONRA PASS.
"""
import json, re, os, sys, py_compile
import urllib.request

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
HERE     = os.path.dirname(os.path.abspath(__file__))

SPEC = r'''
Write `tests/test_authz.py` for Project KASA — pytest security regression tests for the MCP server's
authorization. Use the existing `server_client` fixture (from conftest.py) which yields a dict with
keys "client" (FastAPI TestClient, raise_server_exceptions=False), "token", and "headers"
(Authorization bearer). Endpoints: POST /v1/execute_tool  body {"tool_calls":[{"tool_name":..,
"parameters":{..}}], "agent_id":..}  ; POST /v1/ingest  body {"tool":.., "agent_id":.., "params":{..}}.

Write EXACTLY these three tests (assert the SECURE post-fix behavior, so they FAIL before the fix):

def test_c5_network_cannot_claim_system(server_client):
    """C5: agi_id='system' agodyle gelen istek TUM izinleri baypaslamamali."""
    c, h = server_client["client"], server_client["headers"]
    # 'system' iddiasiyla profile_write dene — govdeden 'system' ASLA kabul edilmemeli
    r = c.post("/v1/execute_tool", headers=h, json={
        "agent_id": "system",
        "tool_calls": [{"tool_name": "profile_write",
                        "parameters": {"key": "user.x", "value": 1, "provenance": []}}]})
    assert r.status_code in (400, 403), f"C5 ACIK: system baypasi kabul edildi -> {r.status_code} {r.text[:200]}"

def test_c7_grant_permission_not_callable(server_client):
    """C7: grant_permission ag disindan cagrilamamali (izin yukseltme)."""
    c, h = server_client["client"], server_client["headers"]
    r = c.post("/v1/ingest", headers=h, json={
        "tool": "grant_permission", "agent_id": "attacker",
        "params": {"scope": "profile:write"}})
    assert r.status_code in (403, 404), f"C7 ACIK: grant_permission cagrilabildi -> {r.status_code} {r.text[:200]}"

def test_c8_private_methods_not_callable(server_client):
    """C8: _check_permission gibi private/allow-list disi metodlar isimle cagrilamamali."""
    c, h = server_client["client"], server_client["headers"]
    for name in ("_check_permission", "_db", "grant_permission"):
        r = c.post("/v1/ingest", headers=h, json={
            "tool": name, "agent_id": "attacker", "params": {}})
        assert r.status_code == 404, f"C8 ACIK: '{name}' cagrilabildi -> {r.status_code} {r.text[:200]}"

Add a Turkish module docstring. Output ONLY one ```python``` block.
'''

CHECK = r'''
1. Uses the server_client fixture dict (client/headers). No new fixtures invented.
2. Three tests test_c5_network_cannot_claim_system / test_c7_grant_permission_not_callable /
   test_c8_private_methods_not_callable with the exact endpoints and asserts as specified.
3. Asserts secure behavior: C5 in (400,403); C7 in (403,404); C8 == 404 for each private name.
4. Valid Python 3, pytest style, no __main__ needed.
'''

def call_model(model, prompt, label, num_predict=2600, temp=0.15):
    print(f"\n[AT] {label} ({model}) ...", flush=True)
    payload = json.dumps({"model": model, "prompt": prompt, "stream": True,
                          "options": {"temperature": temp, "num_predict": num_predict}}).encode()
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    buf = []
    with urllib.request.urlopen(req, timeout=1200) as r:
        for raw in r:
            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            tok = obj.get("response", "")
            buf.append(tok); print(tok, end="", flush=True)
            if obj.get("done"):
                break
    print(); return "".join(buf)

def extract_python(text):
    m = re.search(r"```python\s*\r?\n(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip() + "\n"

def save(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[AT] yazildi: {path}")

def main():
    draft = call_model(DRAFTER, "Generate exactly as specified.\n\n" + SPEC, "TASLAK")
    save(os.path.join(HERE, "authz_test_draft.txt"), draft)
    code = extract_python(draft)
    review = call_model(REVIEWER,
        "Review and FIX against the checklist. Keep the three test names, endpoints, and asserts intact. "
        "Output ONLY the corrected file in one ```python``` block.\n\n=== CHECKLIST ===\n" + CHECK +
        "\n\n=== DRAFT ===\n```python\n" + code[:8000] + "\n```", "REVIEW")
    save(os.path.join(HERE, "authz_test_review.txt"), review)
    final = extract_python(review)
    # kaba dogrulama: 3 test var mi
    for needle in ("test_c5_network_cannot_claim_system", "test_c7_grant_permission_not_callable",
                   "test_c8_private_methods_not_callable", "server_client"):
        if needle not in final:
            print(f"[AT] UYARI: '{needle}' yok — model kacirdi, incele."); sys.exit(2)
    out = "d:/kasa/tests/test_authz.py"
    save(out, final)
    try:
        py_compile.compile(out, doraise=True)
        print("[AT] py_compile: GECTI")
    except py_compile.PyCompileError as e:
        print(f"[AT] py_compile HATA:\n{e}"); sys.exit(1)

if __name__ == "__main__":
    main()
