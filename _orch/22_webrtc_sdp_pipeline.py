"""
KASA Orkestrasyon — Layer #4 ek: WebRTC SDP-filtre kalkani (2. katman) v1.0
deepseek taslak -> qwen review. Cikti: 22_webrtc_sdp_block.js
  -> Claude bunu _PRIVACY_JS icine, mevcut onicecandidate blogundan SONRA splice eder.

Kullanicinin taslagi (setLocalDescription sarma) referans alinir; bilinen 3 hatasi
duzeltilir: (1) sadece SDP filtreler, trickle'i kacirir -> zaten onicecandidate blogu
var, bu VANILLA ICE icin ek kalkan; (2) `=== 'host'` tam-esitlik hatasi -> indexOf ile
esnek eslesme; (3) console.log kaldirilir.
"""
import json, sys, re
import urllib.request

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"

def call_model(model, prompt, label, max_tokens=2560):
    print(f"\n[ORCH] {label} ({model}) cagiriliyor...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": 0.1, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    out = []
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                out.append(obj.get("response", ""))
                print(obj.get("response", ""), end="", flush=True)
                if obj.get("done"):
                    break
            except json.JSONDecodeError:
                continue
    print()
    return "".join(out)

def extract_js(text):
    m = re.search(r"```(?:javascript|js)?\n([\s\S]+?)```", text)
    return m.group(1).strip() if m else text.strip()

DRAFT = r'''You are writing a JavaScript SNIPPET (NOT a full IIFE, NOT a top-level function) that
will be pasted INSIDE an already-running IIFE where a boolean `POISON` already exists
(true only for strict/paranoid). Do NOT redeclare POISON. Do NOT wrap in (function(){}).

This is a SECOND-LAYER WebRTC leak shield that filters ICE candidates found in the SDP
when setLocalDescription is called (covers "vanilla ICE" where candidates are embedded in
the SDP). A separate onicecandidate filter already handles trickle ICE, so ONLY do the
SDP part here.

A user wrote this DRAFT (it has bugs, fix them):

    const orig = window.RTCPeerConnection.prototype.setLocalDescription;
    window.RTCPeerConnection.prototype.setLocalDescription = function(description) {
        if (description && description.sdp) {
            description.sdp = description.sdp.split('\n').filter(line => {
                if (line.startsWith('a=candidate')) {
                    const t = line.split('typ ')[1];      // BUG: "host generation 0.." != "host"
                    if (t === 'host' || t === 'srflx') return false;
                }
                return true;
            }).join('\n');
        }
        return orig.apply(this, arguments);
    };
    console.log(...);   // BUG: remove, leaves a trace

Write the CORRECTED snippet with EXACTLY these fixes/rules:
- Wrap everything in: if (POISON) { try { ... } catch (e) {} }
- Guard: var RTC = window.RTCPeerConnection; if (RTC && RTC.prototype && RTC.prototype.setLocalDescription) { ... }
- Save original: var _origSLD = RTC.prototype.setLocalDescription;
- Replace RTC.prototype.setLocalDescription with function(description) that, if
  (description && description.sdp), rewrites description.sdp by splitting on '\n' and
  DROPPING any line that (startsWith 'a=candidate') AND (indexOf(' typ host') !== -1 OR
  indexOf(' typ srflx') !== -1). Keep every other line (relay + non-candidate). Rejoin with '\n'.
- Use indexOf, NOT strict equality on the type token (that is the main bug).
- Then: return _origSLD.apply(this, arguments);
- NO console.log, NO external requests.
Output ONLY one javascript code block containing the corrected snippet.'''

REVIEW = ('Review this JS snippet meant to be pasted INSIDE an existing IIFE where `POISON` '
    '(bool) exists. Verify: (1) NOT wrapped in its own IIFE/function, does NOT redeclare POISON; '
    '(2) all logic in if (POISON){ try{...}catch(e){} }; (3) guards window.RTCPeerConnection and '
    '.prototype.setLocalDescription existence; (4) saves original then replaces it; (5) filters '
    "description.sdp lines: drops a line only if it startsWith 'a=candidate' AND contains "
    "' typ host' or ' typ srflx' via indexOf (NOT strict equality); keeps relay + other lines; "
    '(6) returns original.apply(this, arguments); (7) NO console.log; (8) valid JS, balanced braces. '
    'Fix any bug. Output ONLY the corrected javascript snippet in one code block.\n\n'
    '```javascript\n{DRAFT}\n```')

def run():
    draft = extract_js(call_model(DRAFTER, DRAFT, "DRAFT — webrtc SDP block"))
    final = extract_js(call_model(REVIEWER, REVIEW.replace("{DRAFT}", draft), "REVIEW — webrtc SDP block"))
    with open("d:/kasa/_orch/22_webrtc_sdp_block.js", "w", encoding="utf-8") as f:
        f.write(final + "\n")
    print("\n[ORCH] yazildi -> 22_webrtc_sdp_block.js")
    print("[ORCH] Claude dogrulayip _PRIVACY_JS icine (onicecandidate blogundan sonra) splice edecek.")

if __name__ == "__main__":
    run()
