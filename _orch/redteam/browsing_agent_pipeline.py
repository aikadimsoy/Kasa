# -*- coding: utf-8 -*-
"""
KASA Red-Team — OTONOM BROWSING AGENT ureticisi (sifir-token)
deepseek taslak -> qwen inceleme -> py_compile -> redteam/browsing_agent.py
Uretilen ajan: kullanici yerine gezer; verilen URL(ler)i ceker ve KASA browser'in
_INGEST_JS'i ile BIREBIR AYNI sekilde :8000'e ingest eder (distill zinciri testi).
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
Write a SINGLE self-contained Python 3 file `browsing_agent.py`, STANDARD LIBRARY ONLY
(argparse, urllib.request, json, os, re, html). It is an AUTONOMOUS browsing agent that visits
URLs on the user's behalf and ingests each page into KASA exactly like the real browser does.

=== FAITHFUL INGEST SHAPE (must match the KASA browser's _INGEST_JS -> KasaApi._post) ===
Read bearer token from d:/kasa/kasa.toml (regex bearer_token = "..."), call it TOKEN.
For each visited URL:
  - fetch the page: urllib GET with a normal-looking User-Agent, read HTML (utf-8, errors=replace).
  - title: extract <title>...</title> (regex, else "").
  - text: approximate document.body.innerText -> remove <script>/<style> blocks, strip ALL html
    tags, unescape html entities (html.unescape), collapse whitespace, take first 3000 chars.
  - POST to http://localhost:8000/v1/ingest with header Authorization: Bearer TOKEN, body EXACTLY:
      {"tool":"event_ingest","agent_id":"browser",
       "params":{"source":"browser","type":"page_visit",
                 "content":{"url":url,"title":title,"text":text,"cookies":[]},
                 "ttl_days":30}}
  - print: "[AGENT] visited {url} | title='{title}' | text_len={len} | ingest -> {status/response}"
  - catch errors per-URL (never crash the whole run; print "[AGENT][ERR] {url}: {e}").

=== CLI ===
  --urls U1 U2 ...   : one or more URLs to visit (required).
  Default if none given: ["http://127.0.0.1:8901/poison"].
Print a final line "[AGENT] done: N pages ingested". Turkish comments. Output ONLY one ```python``` block.
'''

CHECK = r'''
1. Reads bearer_token from d:/kasa/kasa.toml.
2. Strips <script>/<style>, removes tags, html.unescape, collapses whitespace, first 3000 chars.
3. POST body EXACTLY matches the browser shape (tool/agent_id/source/type/content keys, ttl_days).
4. Sends Authorization: Bearer TOKEN. Per-URL try/except; never crashes the run.
5. argparse --urls with the given default. Valid Python 3, stdlib only.
'''

def call_model(model, prompt, label, num_predict=3500, temp=0.15):
    print(f"\n[BA] {label} ({model}) ...", flush=True)
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
    print(f"[BA] yazildi: {path}")

def main():
    draft = call_model(DRAFTER, "Generate exactly as specified.\n\n" + SPEC, "TASLAK")
    save(os.path.join(HERE, "browsing_agent_draft.txt"), draft)
    code = extract_python(draft)
    review = call_model(REVIEWER,
        "Review and FIX against the checklist. Ensure the POST body matches the browser shape EXACTLY. "
        "Output ONLY the corrected file in one ```python``` block.\n\n=== CHECKLIST ===\n" + CHECK +
        "\n\n=== DRAFT ===\n```python\n" + code[:8500] + "\n```", "REVIEW")
    save(os.path.join(HERE, "browsing_agent_review.txt"), review)
    final = extract_python(review)
    out = os.path.join(HERE, "browsing_agent.py")
    save(out, final)
    try:
        py_compile.compile(out, doraise=True)
        print("[BA] py_compile: GECTI")
    except py_compile.PyCompileError as e:
        print(f"[BA] py_compile HATA:\n{e}"); sys.exit(1)

if __name__ == "__main__":
    main()
