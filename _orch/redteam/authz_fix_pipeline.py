# -*- coding: utf-8 -*-
"""
KASA — MCP authz (C5/C7/C8) FIX ureticisi (sifir-token)
deepseek taslak -> qwen inceleme -> py_compile -> src/mcp_server/server.py (yedekli)
Emirler: (C5) RESERVED_AGENT_IDS govdeden 'system' reddi; (C8) PUBLIC_TOOLS allow-list;
(C7) grant_permission zaten allow-list disinda kalir; PermissionError->403.
Sadece server.py'yi regenere eder; tools.py'deki grant_permission admin-gate ayri splice edilir.
"""
import json, re, os, sys, py_compile, shutil, time
import urllib.request

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
HERE     = os.path.dirname(os.path.abspath(__file__))
SERVER   = "d:/kasa/src/mcp_server/server.py"

with open(SERVER, encoding="utf-8") as f:
    CURRENT = f.read()

SPEC = r'''
You are hardening Project KASA's MCP server file `src/mcp_server/server.py` against three PROVEN
authorization vulnerabilities. Below is the CURRENT full file. Return the COMPLETE fixed file.
Preserve ALL existing behavior (imports, Pydantic models, lifespan, CORS, verify_token, the
health_check, start_server, __main__) EXCEPT make EXACTLY these changes:

CHANGE 1 — add two module-level constants right after the imports (top of file, before the models):
    RESERVED_AGENT_IDS = {"system"}
    PUBLIC_TOOLS = {"event_ingest", "profile_read", "profile_write", "forget",
                    "audit_read", "prune_expired_events"}

CHANGE 2 (C5) — in BOTH endpoints execute_tool and ingest, BEFORE building VaultTools, reject a
client-supplied privileged identity:
    if request.agent_id in RESERVED_AGENT_IDS:
        raise HTTPException(status_code=403, detail="agent_id ayrilmis (system ag disindan iddia edilemez).")

CHANGE 3 (C8) — replace the `hasattr(tool_handler, ...)` gate in BOTH endpoints with a strict
allow-list check. In execute_tool, for each tool_call use tool_call.tool_name; in ingest use
request.tool. If the name is NOT in PUBLIC_TOOLS, raise HTTPException status_code=404 with detail
f"Arac bulunamadi: '{name}'". Do NOT use hasattr anymore.

CHANGE 4 — in execute_tool, wrap the `method(**params)` call so PermissionError -> HTTPException 403
(currently only ingest does this; execute_tool leaks 500). Keep the existing TypeError -> 422.

Do not change anything else. Keep verify_token Security dependency on both endpoints. Output ONLY the
complete fixed file in one ```python``` block.

=== CURRENT FILE ===
''' + "```python\n" + CURRENT + "\n```"

CHECK = r'''
1. RESERVED_AGENT_IDS = {"system"} and PUBLIC_TOOLS = {...six tool names...} present at module level.
2. Both execute_tool and ingest reject request.agent_id in RESERVED_AGENT_IDS with HTTPException 403.
3. Both endpoints use `not in PUBLIC_TOOLS` -> 404; NO hasattr calls remain anywhere.
4. execute_tool catches PermissionError -> 403 and TypeError -> 422.
5. verify_token still guards both endpoints; lifespan/CORS/health/start_server unchanged. Valid Python 3.
'''

def call_model(model, prompt, label, num_predict=4096, temp=0.1):
    print(f"\n[AF] {label} ({model}) ...", flush=True)
    payload = json.dumps({"model": model, "prompt": prompt, "stream": True,
                          "options": {"temperature": temp, "num_predict": num_predict}}).encode()
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    buf = []
    with urllib.request.urlopen(req, timeout=1800) as r:
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
    print(f"[AF] yazildi: {path}")

def main():
    draft = call_model(DRAFTER, SPEC, "TASLAK", num_predict=4096)
    save(os.path.join(HERE, "authz_fix_draft.txt"), draft)
    code = extract_python(draft)
    review = call_model(REVIEWER,
        "Review and FIX against the checklist; ensure the changes are present and nothing else broke. "
        "Output ONLY the complete corrected file in one ```python``` block.\n\n=== CHECKLIST ===\n" + CHECK +
        "\n\n=== DRAFT ===\n```python\n" + code[:13000] + "\n```", "REVIEW", num_predict=4096)
    save(os.path.join(HERE, "authz_fix_review.txt"), review)
    final = extract_python(review)

    cand = os.path.join(HERE, "server_fixed.py")
    save(cand, final)
    try:
        py_compile.compile(cand, doraise=True)
        print("[AF] py_compile: GECTI")
    except py_compile.PyCompileError as e:
        print(f"[AF] py_compile HATA:\n{e}"); sys.exit(1)
    # kritik parcalar duruyor mu? + guvenlik regresyon guard'lari
    must_have = ("RESERVED_AGENT_IDS", "PUBLIC_TOOLS", "def execute_tool", "def ingest",
                 "verify_token", "def lifespan", "def start_server", "PermissionError")
    must_not  = ("hasattr(",)  # allow-list hasattr'i tamamen kaldirmali
    for needle in must_have:
        if needle not in final:
            print(f"[AF] UYARI: '{needle}' YOK — splice EDILMEDI, incele."); sys.exit(2)
    for bad in must_not:
        if bad in final:
            print(f"[AF] UYARI: hala '{bad}' var — allow-list eksik, splice EDILMEDI."); sys.exit(3)
    bak = SERVER + ".bak_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(SERVER, bak)
    print(f"[AF] yedek: {bak}")
    save(SERVER, final)
    print("[AF] server.py guncellendi.")

if __name__ == "__main__":
    main()
