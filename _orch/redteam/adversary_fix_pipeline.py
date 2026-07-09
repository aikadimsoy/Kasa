# -*- coding: utf-8 -*-
"""
KASA Red-Team — adversary_site.py DUZELTME turu (sifir-token).
Ilk tur model parmak-izini SUNUCU tarafinda uydurmus (yanlis). Bu turda JS toplayici
ZORUNLU SABLON olarak veriliyor; model yalnizca Python http.server iskeletini dogru kurar.
deepseek taslak -> qwen inceleme -> py_compile.
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

# Bu HTML+JS AYNEN kullanilacak — tarayicida CALISIR, gercek kimligi okur.
PAGE_HTML = r'''<!doctype html><html><head><meta charset="utf-8"><title>fp</title></head>
<body><p id="msg">KASA adversary site — collecting...</p>
<script>
async function collect(){
  const fp={};
  try{fp.userAgent=navigator.userAgent;}catch(e){}
  try{fp.platform=navigator.platform;}catch(e){}
  try{fp.language=navigator.language;}catch(e){}
  try{fp.languages=navigator.languages;}catch(e){}
  try{fp.hardwareConcurrency=navigator.hardwareConcurrency;}catch(e){}
  try{fp.deviceMemory=navigator.deviceMemory;}catch(e){}
  try{fp.screen=[screen.width,screen.height,screen.colorDepth];}catch(e){}
  try{fp.timezone=Intl.DateTimeFormat().resolvedOptions().timeZone;}catch(e){}
  try{fp.tzOffset=new Date().getTimezoneOffset();}catch(e){}
  try{const c=document.createElement('canvas');const x=c.getContext('2d');
    x.textBaseline='top';x.font='14px Arial';x.fillText('KASA-fp-☃',2,2);
    const d=c.toDataURL();let h=0;for(let i=0;i<d.length;i++){h=(h*31+d.charCodeAt(i))>>>0;}
    fp.canvasHash=h.toString(16);}catch(e){fp.canvasHash=null;}
  try{const gl=document.createElement('canvas').getContext('webgl');
    const dbg=gl.getExtension('WEBGL_debug_renderer_info');
    fp.webglVendor=gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL);
    fp.webglRenderer=gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL);}catch(e){fp.webglVendor=null;fp.webglRenderer=null;}
  fp.webrtc=[];
  try{const pc=new RTCPeerConnection({iceServers:[]});pc.createDataChannel('x');
    pc.onicecandidate=(ev)=>{if(ev&&ev.candidate)fp.webrtc.push(ev.candidate.candidate);};
    await pc.createOffer().then(o=>pc.setLocalDescription(o));
    await new Promise(r=>setTimeout(r,1500));}catch(e){}
  try{await fetch('/collect',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({js:fp})});}catch(e){}
  document.getElementById('msg').textContent='KASA adversary site — fingerprint captured';
}
collect();
</script></body></html>'''

SPEC = r'''
Write a SINGLE self-contained Python 3 file `adversary_site.py`, STANDARD LIBRARY ONLY
(http.server, socketserver, json, os, time). It is a local fingerprinting site on
127.0.0.1:8901 that records how a visiting browser looks FROM THE OUTSIDE.

HARD RULES:
- DO NOT compute any fingerprint in Python. DO NOT call os.uname(), os.cpu_count(),
  time.strftime for the fingerprint. The browser's JavaScript does ALL fingerprint reading.
- GET "/" MUST return the EXACT html page provided below (verbatim, unchanged), as
  Content-Type text/html; charset=utf-8. Store it as a module-level string PAGE_HTML.
- POST "/collect": read Content-Length bytes, json.loads the body -> {"js": {...}}. If the
  body is empty or invalid JSON, respond 400 {"ok":false} without crashing. Capture
  SERVER-SIDE from request headers:
      accept_language = self.headers.get("Accept-Language","")
      user_agent      = self.headers.get("User-Agent","")
      sec_ch_ua       = self.headers.get("sec-ch-ua","")
      client_ip       = self.client_address[0]
  Build record = {"ts": time.time(),
                  "http": {accept_language, user_agent, sec_ch_ua, client_ip},
                  "js": body["js"]}. Append ONE json line to
  os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures.jsonl").
  Respond 200 {"ok":true}.
- After writing, PRINT a consistency verdict:
    js_lang = (record["js"].get("language") or "")
    http_lang_first = accept_language.split(",")[0].strip() if accept_language else ""
    if js_lang and http_lang_first and js_lang.lower() != http_lang_first.lower():
        print(f"[LEAK] layer mismatch: js.language={js_lang} vs http.accept_language={http_lang_first}")
    else:
        print(f"[OK] language layers consistent (js={js_lang}, http={http_lang_first})")
    Also print: f"[INFO] js.timezone={...} tzOffset={...} platform={...} ua={...[:60]}"
- Use ThreadingHTTPServer (http.server.ThreadingHTTPServer if available, else a
  socketserver.ThreadingMixIn + HTTPServer subclass). Silence default logging (override
  log_message to pass) so only our verdicts print. main guard prints the URL then serve_forever().
- Turkish comments. Output ONLY the complete file in ONE ```python``` block.

=== PAGE_HTML (use verbatim as the GET / body) ===
''' + '<<<PAGE_HTML_PLACEHOLDER>>>'

CHECK = r'''
1. NO server-side fingerprint computation; no os.uname/os.cpu_count. GET / returns PAGE_HTML verbatim.
2. POST /collect parses {"js":...}, handles empty/invalid body -> 400 without crashing.
3. Captures Accept-Language/User-Agent/sec-ch-ua/client_ip server-side from self.headers.
4. Appends one JSON line per capture to captures.jsonl beside the script.
5. Prints [LEAK]/[OK] verdict exactly comparing js.language vs first Accept-Language tag.
6. ThreadingHTTPServer bound to 127.0.0.1:8901; log_message silenced; serve_forever in main.
7. Valid Python 3, Windows-safe, stdlib only.
'''

def call_model(model, prompt, label, num_predict=4096, temp=0.15):
    print(f"\n[ADVFIX] {label} ({model}) ...", flush=True)
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
    print(f"[ADVFIX] yazildi: {path}")

def main():
    spec = SPEC.replace('<<<PAGE_HTML_PLACEHOLDER>>>', PAGE_HTML)
    draft = call_model(DRAFTER, "Generate exactly as specified.\n\n" + spec, "TASLAK")
    save(os.path.join(HERE, "adversary_fix_draft.txt"), draft)
    code = extract_python(draft)
    review = call_model(REVIEWER,
        "Review and FIX against the checklist. Ensure PAGE_HTML is embedded verbatim and GET / "
        "returns it unchanged. Output ONLY the corrected file in one ```python``` block.\n\n"
        "=== CHECKLIST ===\n" + CHECK + "\n\n=== DRAFT ===\n```python\n" + code[:9500] + "\n```",
        "REVIEW")
    save(os.path.join(HERE, "adversary_fix_review.txt"), review)
    final = extract_python(review)
    out = os.path.join(HERE, "adversary_site.py")
    save(out, final)
    try:
        py_compile.compile(out, doraise=True)
        print("[ADVFIX] py_compile: GECTI")
    except py_compile.PyCompileError as e:
        print(f"[ADVFIX] py_compile HATA:\n{e}"); sys.exit(1)

if __name__ == "__main__":
    main()
