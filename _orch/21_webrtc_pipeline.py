"""
KASA Orkestrasyon — Layer #4: WebRTC IP Sizinti Onleme v1.0
deepseek taslak -> qwen review. Cikti: 21_webrtc_block.js
  -> Claude bunu _PRIVACY_JS icine (kapanis })(); ONCESI) splice eder.

Amac: proxy/VPN kullanilsa bile WebRTC'nin STUN uzerinden gercek yerel + genel IP'yi
sizdirmasini engellemek. Blok _PRIVACY_JS IIFE'si icinde calisir; oradaki `POISON`
(bool, strict/paranoid'de true) ve `LEVEL` degiskenleri kapsamda mevcuttur.
"""
import json, sys, re
import urllib.request

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"

def call_model(model, prompt, label, max_tokens=3072):
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

DRAFT = r'''You are writing a JavaScript SNIPPET (NOT a full IIFE, NOT a function) that will be
pasted INSIDE an already-running IIFE. In that scope these variables already exist:
  - POISON : boolean, true only when privacy level is strict or paranoid
  - LEVEL  : string
Do NOT redeclare them. Do NOT wrap in (function(){...})().

Goal: stop WebRTC from leaking the user's real local and public IP addresses (a classic
leak that bypasses VPN/proxy). Only act when POISON is true.

Write EXACTLY this shape:

if (POISON) {
  try {
    var _OrigRTC = window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection;
    if (_OrigRTC) {
      // A candidate string leaks an IP if it contains " typ host" or " typ srflx".
      // Return true if the candidate event should be DROPPED (suppressed).
      var _isLeaky = function(ev) {
        if (!ev || !ev.candidate || !ev.candidate.candidate) return false;
        var c = ev.candidate.candidate;
        return (c.indexOf(' typ host') !== -1) || (c.indexOf(' typ srflx') !== -1);
      };
      var _Wrapped = function(config, constraints) {
        var pc = new _OrigRTC(config, constraints);
        // 1) Wrap addEventListener so 'icecandidate' listeners never see leaky candidates.
        var _origAdd = pc.addEventListener.bind(pc);
        pc.addEventListener = function(type, listener, opts) {
          if (type === 'icecandidate' && typeof listener === 'function') {
            return _origAdd(type, function(ev) { if (_isLeaky(ev)) return; return listener(ev); }, opts);
          }
          return _origAdd(type, listener, opts);
        };
        // 2) Wrap the onicecandidate property setter the same way.
        var _userCb = null;
        try {
          Object.defineProperty(pc, 'onicecandidate', {
            configurable: true,
            get: function() { return _userCb; },
            set: function(fn) {
              _userCb = fn;
              _origAdd('icecandidate', function(ev) {
                if (_isLeaky(ev)) return;
                if (typeof _userCb === 'function') _userCb(ev);
              });
            }
          });
        } catch (e) {}
        return pc;
      };
      _Wrapped.prototype = _OrigRTC.prototype;
      window.RTCPeerConnection = _Wrapped;
      if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = _Wrapped;
      if (window.mozRTCPeerConnection) window.mozRTCPeerConnection = _Wrapped;
    }
  } catch (e) {}
}

Requirements: keep this exact behavior and structure, ensure valid JS with balanced braces,
no console.log, no external requests. Output ONLY one javascript code block with this snippet.'''

REVIEW = ('Review this JavaScript snippet meant to be pasted INSIDE an existing IIFE where '
    '`POISON` (bool) already exists. Verify: (1) does NOT redeclare POISON/LEVEL, is NOT wrapped '
    'in its own IIFE or function, (2) entire logic guarded by if (POISON){ try {...} catch(e){} }, '
    '(3) reads window.RTCPeerConnection || webkitRTCPeerConnection || mozRTCPeerConnection, '
    '(4) _isLeaky drops candidates containing " typ host" or " typ srflx", (5) wraps BOTH '
    "pc.addEventListener('icecandidate') AND the onicecandidate property setter to filter, "
    '(6) _Wrapped.prototype = _OrigRTC.prototype and reassigns window.RTCPeerConnection (+webkit/moz), '
    '(7) valid JS, balanced braces, no console.log. Fix any bug. '
    'Output ONLY the corrected javascript snippet in one code block.\n\n```javascript\n{DRAFT}\n```')

def run():
    draft = extract_js(call_model(DRAFTER, DRAFT, "DRAFT — webrtc block"))
    final = extract_js(call_model(REVIEWER, REVIEW.replace("{DRAFT}", draft), "REVIEW — webrtc block"))
    with open("d:/kasa/_orch/21_webrtc_block.js", "w", encoding="utf-8") as f:
        f.write(final + "\n")
    print("\n[ORCH] yazildi -> 21_webrtc_block.js")
    print("[ORCH] Claude dogrulayip _PRIVACY_JS kapanisindan once splice edecek.")

if __name__ == "__main__":
    run()
