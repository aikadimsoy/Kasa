# -*- coding: utf-8 -*-
"""
KASA Red-Team — ADVERSARY parmak-izi sitesi ureticisi (sifir-token) v1.0
deepseek-coder-v2 taslak -> qwen2.5-coder inceleme -> py_compile -> redteam/adversary_site.py

Uretilecek dosya: harici bir saldirgan sitesinin gordugu KIMLIGI yakalar.
KRITIK fikir: JS katmani (navigator.language vs.) ile HTTP katmani (Accept-Language basligi)
CELISKISINI ortaya cikarir -> KASA'nin #1 deanon acigini (hardcoded de-DE) canli kanitlar.
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
Write a SINGLE self-contained Python file `adversary_site.py` using ONLY the standard
library (http.server, json, time, os, hashlib). It is a local "malicious" fingerprinting
site that a privacy browser will visit; it records how the browser looks FROM THE OUTSIDE.

Requirements:
- Class-based http.server.BaseHTTPRequestHandler + ThreadingHTTPServer on 127.0.0.1:8901.
- GET "/" -> return an HTML page (Content-Type text/html) that, on load, runs JS to collect a
  fingerprint object `fp` with these fields:
    fp.js = {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      languages: navigator.languages,           // array
      hardwareConcurrency: navigator.hardwareConcurrency,
      deviceMemory: navigator.deviceMemory,
      screen: [screen.width, screen.height, screen.colorDepth],
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      tzOffset: new Date().getTimezoneOffset(),
      canvasHash: (draw text "KASA-fp-☃" to a <canvas> then a simple hash of toDataURL),
      webglVendor / webglRenderer: from WebGLRenderingContext UNMASKED_VENDOR_WEBGL /
                                   UNMASKED_RENDERER_WEBGL (wrap in try/catch, null if blocked),
      webrtc: []  // best-effort: create RTCPeerConnection, createDataChannel, createOffer,
                  // collect candidate.candidate strings for ~1.5s (try/catch, ok if empty)
    }
  Then POST fp as JSON to "/collect" with fetch(). Show a short on-page message so a human
  watching the browser sees "KASA adversary site — fingerprint captured".
- POST "/collect" -> read JSON body (the fp.js). ALSO capture SERVER-SIDE from the request
  headers: accept_language = self.headers.get("Accept-Language"),
           user_agent      = self.headers.get("User-Agent"),
           sec_ch_ua       = self.headers.get("sec-ch-ua"),
           client_ip       = self.client_address[0].
  Build a record: {"ts":time.time(), "http":{accept_language,user_agent,sec_ch_ua,client_ip},
                   "js": <posted fp>}. Append it as one JSON line to
  os.path.join(HERE, "captures.jsonl") where HERE = dir of this file. Respond 200 {"ok":true}.
- After writing, PRINT to stdout a concise CONSISTENCY VERDICT comparing layers:
    * JS language (e.g. "de-DE") vs HTTP Accept-Language header first tag.
      If they DISAGREE -> print "[LEAK] layer mismatch: js.language=X vs http.accept_language=Y"
      (this is the deanonymization signal). If agree -> "[OK] language layers consistent".
    * Also print js.timezone and js.tzOffset next to js.language so a human can eyeball
      whether timezone/lang/UA tell a consistent regional story.
- Add a main guard: print the URL, serve_forever(). Add Turkish comments.
- Keep the JS robust: wrap every probe in try/catch so one failure doesn't blank the whole fp.

Output ONLY the complete Python file in a single ```python ... ``` block.
'''

CHECK = r'''
1. Pure stdlib only (no flask/requests). ThreadingHTTPServer on 127.0.0.1:8901.
2. GET / serves valid HTML with the JS collector; POST /collect parses JSON body safely
   (handle empty/invalid body without crashing -> 400).
3. Server-side capture of Accept-Language, User-Agent, sec-ch-ua, client_ip from self.headers.
4. Appends one JSON line per capture to captures.jsonl next to the script (HERE).
5. Prints the [LEAK]/[OK] language-layer consistency verdict comparing js.language vs
   http Accept-Language.
6. Every JS probe in try/catch; canvas/webgl/webrtc failures degrade gracefully.
7. Valid Python 3, no syntax errors, main guard calls serve_forever().
'''

def call_model(model, prompt, label, num_predict=4096, temp=0.2):
    print(f"\n[ADV] {label} ({model}) ...", flush=True)
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
    print(f"[ADV] yazildi: {path}")

def main():
    draft_prompt = ("Generate the file exactly as specified. Output ONLY one ```python``` block.\n\n" + SPEC)
    draft = call_model(DRAFTER, draft_prompt, "TASLAK")
    save(os.path.join(HERE, "adversary_draft.txt"), draft)
    code = extract_python(draft)

    review_prompt = ("Review and FIX this Python file against the checklist. Output ONLY the corrected "
                     "complete file in one ```python``` block, then a one-line Turkish summary.\n\n"
                     "=== CHECKLIST ===\n" + CHECK + "\n\n=== DRAFT ===\n```python\n" + code[:9000] + "\n```")
    review = call_model(REVIEWER, review_prompt, "REVIEW")
    save(os.path.join(HERE, "adversary_review.txt"), review)
    final = extract_python(review)

    out = os.path.join(HERE, "adversary_site.py")
    save(out, final)
    try:
        py_compile.compile(out, doraise=True)
        print("[ADV] py_compile: GECTI")
    except py_compile.PyCompileError as e:
        print(f"[ADV] py_compile HATA:\n{e}"); sys.exit(1)

if __name__ == "__main__":
    main()
