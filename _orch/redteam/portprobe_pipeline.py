# -*- coding: utf-8 -*-
"""
KASA Red-Team — :8000 PORT/GUVENLIK probe ureticisi (sifir-token) v1.0
deepseek taslak -> qwen inceleme -> py_compile -> redteam/port_probe.py
Uretilen script CANLI 127.0.0.1:8000 sunucusuna saldirir, her kontrolu
SECURE (savundu) / VULNERABLE (acik) diye siniflar, probe_results.json yazar.
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
Write a SINGLE self-contained Python 3 file `port_probe.py`, STANDARD LIBRARY ONLY
(urllib.request, json, os, time). It red-teams a LIVE KASA MCP server and classifies each
check as SECURE or VULNERABLE, writing results to probe_results.json (beside the script)
and printing a readable line per check.

=== TARGET FACTS ===
BASE = "http://127.0.0.1:8000"
Read the bearer token from d:/kasa/kasa.toml line `bearer_token = "..."` (simple regex);
call it TOKEN. AUTH = {"Authorization": f"Bearer {TOKEN}", "Content-Type":"application/json"}.

Endpoints:
  GET  /                -> 200 {"status":"ok"}   (no auth)
  POST /v1/execute_tool  body {"tool_calls":[{"tool_name":str,"parameters":{...}}],"agent_id":str}
                         Bearer REQUIRED. 404 if tool_name not an attribute; 422 bad params.
                         Response {"results":[{"tool_name":str,"result":{...}}]}.
  POST /v1/ingest        body {"tool":str,"agent_id":str,"params":{...}}  Bearer REQUIRED.
                         Response {"result":{...}}; 401 no/bad token; 403 PermissionError.
Tools & required scope: event_ingest(events:write), profile_write(profile:write),
  profile_read(profile:read:<scope>), forget(admin:forget), audit_read(audit:read),
  grant_permission(scope)  <-- NOTE: grant_permission has NO permission check in code.
Permission model: agent_id is CLIENT-SUPPLIED. agent_id=="system" BYPASSES all checks.
Others are deny-by-default unless a permissions row exists.

Provide a helper post(path, body, headers) -> (status_code, json_or_text) using urllib,
catching HTTPError so 4xx/5xx are returned not raised.

=== CHECKS (implement each; classify SECURE/VULNERABLE with the given rule) ===
C1 health: GET / -> expect 200. (informational; SECURE if 200)
C2 no_token: POST /v1/ingest WITHOUT Authorization, body event_ingest/system ->
   SECURE if status in (401,403); else VULNERABLE.
C3 wrong_token: same with Authorization "Bearer deadbeef" -> SECURE if 401; else VULNERABLE.
C4 baseline_write: /v1/ingest with AUTH, agent_id="system", tool event_ingest,
   params {source:"probe",type:"t",content:{"a":1}} -> expect 200 result.status success
   (baseline that the API works; SECURE if 200).
C5 system_privilege_bypass: /v1/execute_tool with AUTH, agent_id="system",
   tool_calls=[{tool_name:"profile_write",parameters:{key:"pwn.sys",value:"x",provenance:[]}}]
   -> if it returns 200 with a success result, the permission layer was bypassed merely by
   CLAIMING agent_id="system": classify VULNERABLE (self-asserted privileged identity).
   SECURE only if denied.
C6 deny_by_default: /v1/execute_tool AUTH, agent_id="attacker_random", tool_calls=
   [{tool_name:"profile_write",parameters:{key:"pwn.a",value:"x",provenance:[]}}] ->
   SECURE if denied (403 or a PermissionError surfaced / non-success). VULNERABLE if success.
C7 grant_permission_escalation: as agent_id="attacker_random" first call execute_tool
   tool_calls=[{tool_name:"grant_permission",parameters:{scope:"profile:write"}}], THEN retry
   the C6 profile_write as the SAME agent_id. If the second write now SUCCEEDS, the attacker
   escalated its own privileges via the unprotected grant_permission: classify VULNERABLE.
   SECURE if grant_permission is rejected or the later write is still denied.
C8 private_method_exposure: /v1/execute_tool AUTH, agent_id="attacker_random",
   tool_calls=[{tool_name:"_check_permission",parameters:{scope:"x"}}]. Because the server
   uses hasattr() with no allow-list, private/helper methods may be invokable. SECURE if the
   server returns 404 (method not exposed); VULNERABLE if it returns 200 (private method ran).
C9 cors_reflection: GET / with header Origin "https://evil.example". Inspect response header
   Access-Control-Allow-Origin. SECURE if it is absent or NOT "https://evil.example";
   VULNERABLE if it reflects evil origin.
C10 sql_injection_content: /v1/ingest AUTH agent_id="system" event_ingest with
   content {"x":"'); DROP TABLE events;--"} then read back via execute_tool audit_read or a
   second ingest -> SECURE if server still healthy (GET / == 200) and no error (params are
   parametrized). VULNERABLE if the server errors/crashes.
C11 oversized_source: /v1/ingest AUTH system event_ingest source = "A"*5000 -> the code
   raises ValueError (source>64). SECURE if handled (status 4xx/5xx WITHOUT crashing; GET /
   still 200 afterwards). VULNERABLE if it crashes the server (health fails after).

Build results = list of {check, verdict:"SECURE"|"VULNERABLE", status, detail}. Print each as
"[SECURE]/[VULN] Cn name -> detail". At the end print a summary count and dump
probe_results.json. Add Turkish comments. Output ONLY one ```python``` block.
'''

CHECK = r'''
1. Reads bearer_token from d:/kasa/kasa.toml via regex.
2. post() helper catches urllib HTTPError -> returns (code, body) instead of raising.
3. All 11 checks implemented with the EXACT classification rules given.
4. C5/C6/C7/C8 correctly parse whether the tool call SUCCEEDED (result present / status success)
   vs was denied (403 / error string / non-success) to decide VULNERABLE vs SECURE.
5. C9 reads the actual Access-Control-Allow-Origin response header.
6. C10/C11 re-check GET / afterward to confirm the server did not crash.
7. Writes probe_results.json and prints a summary. Valid Python 3, stdlib only.
'''

def call_model(model, prompt, label, num_predict=4096, temp=0.15):
    print(f"\n[PROBE] {label} ({model}) ...", flush=True)
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
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[PROBE] yazildi: {path}")

def main():
    draft = call_model(DRAFTER, "Generate exactly as specified.\n\n" + SPEC, "TASLAK")
    save(os.path.join(HERE, "portprobe_draft.txt"), draft)
    code = extract_python(draft)
    review = call_model(REVIEWER,
        "Review and FIX against the checklist. Ensure verdict logic matches the rules exactly. "
        "Output ONLY the corrected file in one ```python``` block.\n\n"
        "=== CHECKLIST ===\n" + CHECK + "\n\n=== DRAFT ===\n```python\n" + code[:9500] + "\n```",
        "REVIEW")
    save(os.path.join(HERE, "portprobe_review.txt"), review)
    final = extract_python(review)
    out = os.path.join(HERE, "port_probe.py")
    save(out, final)
    try:
        py_compile.compile(out, doraise=True)
        print("[PROBE] py_compile: GECTI")
    except py_compile.PyCompileError as e:
        print(f"[PROBE] py_compile HATA:\n{e}"); sys.exit(1)

if __name__ == "__main__":
    main()
