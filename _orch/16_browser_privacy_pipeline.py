"""
KASA Orkestrasyon — Browser Privacy Decoy v1.0
deepseek-coder-v2:16b taslak -> qwen2.5-coder:14b review
Cikti: browser_window.py icine _PRIVACY_JS sabiti + on_loaded() enjeksiyonu
"""
import json, sys, textwrap, re, os, shutil, datetime, py_compile

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
TARGET   = "d:/kasa/src/browser/browser_window.py"

def call_model(model: str, prompt: str, label: str, max_tokens: int = 8192) -> str:
    print(f"\n[ORCH] {label} ({model}) cagiriliyor...", flush=True)
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.15, "num_predict": max_tokens}
    }).encode()
    import urllib.request
    req = urllib.request.Request(OLLAMA, data=payload,
                                 headers={"Content-Type": "application/json"})
    result = []
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw_line in resp:
            line = raw_line.decode().strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                token = obj.get("response", "")
                result.append(token)
                print(token, end="", flush=True)
                if obj.get("done"):
                    break
            except json.JSONDecodeError:
                continue
    print()
    return "".join(result)

def extract_js(text: str) -> str:
    """Markdown kod blogundan JS'i cek; yoksa ham metni dondur."""
    m = re.search(r"```(?:javascript|js)?\n([\s\S]+?)```", text)
    return m.group(1).strip() if m else text.strip()

# ── DRAFT PROMPT ──────────────────────────────────────────────────────────────
DRAFT_PROMPT = """You are writing a JavaScript IIFE that will be injected into every page
loaded in the KASA browser (via pywebview evaluate_js, runs after page load).

Goal: deceive ad/analytics trackers by replacing their real data with randomized,
consistent-within-session fake values. The user wants to remain anonymous and
feed plausible but fake signals to trackers.

Write a single JavaScript IIFE called `_PRIVACY_JS` that does ALL of the following:

## 1. Fake Geolocation
Override navigator.geolocation.getCurrentPosition and watchPosition.
Return a random European city coordinate that stays fixed for the session:
Pick randomly from this list each page load (but store in sessionStorage so it
stays consistent within a tab session):
[
  {lat:48.8566, lon:2.3522,   city:"Paris"},
  {lat:52.5200, lon:13.4050,  city:"Berlin"},
  {lat:51.5074, lon:-0.1278,  city:"London"},
  {lat:41.9028, lon:12.4964,  city:"Rome"},
  {lat:40.4168, lon:-3.7038,  city:"Madrid"},
  {lat:53.3498, lon:-6.2603,  city:"Dublin"},
  {lat:59.9139, lon:10.7522,  city:"Oslo"},
  {lat:50.0755, lon:14.4378,  city:"Prague"}
]
Add small random noise (+/- 0.01 degrees) each call.
accuracy: 10 + Math.random()*20

## 2. Canvas Fingerprint Poisoning
Override HTMLCanvasElement.prototype.toDataURL and
CanvasRenderingContext2D.prototype.getImageData.
Before returning, XOR a random single-byte value (stored per-session in
sessionStorage as _kp_canvas_seed) against every 4th byte of the pixel data.
This changes the fingerprint hash without visibly affecting rendering.

## 3. WebGL Fingerprint Poisoning
Override WebGLRenderingContext.prototype.getParameter.
For RENDERER and VENDOR strings, return from this fake set:
RENDERER options: ["ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                   "ANGLE (AMD, Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)",
                   "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11)"]
VENDOR options: ["Google Inc. (Intel)", "Google Inc. (AMD)", "Google Inc. (NVIDIA)"]
Pick one per session (sessionStorage key _kp_webgl_idx), keep consistent.
All other getParameter calls pass through to original.

## 4. Navigator Property Spoofing
Override (Object.defineProperty) these navigator properties to fixed fake values:
- hardwareConcurrency: random even number 4,6,8 (session-stable)
- deviceMemory: random from [4, 8] (session-stable)
- platform: "Win32"  (always, no need to randomize)
- languages: ["de-DE", "de", "en-US", "en"] (fake German browser)
- language: "de-DE"

## 5. Screen Spoofing
Override screen properties:
- width: 1920, height: 1080, availWidth: 1920, availHeight: 1040
- colorDepth: 24, pixelDepth: 24

## 6. Timezone Noise
Override Intl.DateTimeFormat to always return "Europe/Berlin" as timeZone
when resolvedOptions() is called. Also override Date.prototype.getTimezoneOffset
to return -60 (Berlin UTC+1) always.

## 7. Known Tracker Cookie Poisoning
Read document.cookie. For each of these cookie name patterns, if found,
replace the value with a randomly generated fake token of similar length and
character set (alphanumeric + common special chars):
Patterns to poison: ["_px", "_abck", "bm_", "dtCookie", "_pxvid", "__pxvid",
                     "_pk_id", "_pk_ses", "_twpid", "RT", "bm_sv", "bm_sz", "bm_mi"]
Write the poisoned cookies back via document.cookie with same path/domain attributes.
Note: some cookies are HttpOnly and cannot be read/written from JS — skip those silently.

## 8. Session Storage seed init
At the top of the IIFE, initialize all session seeds if not already set:
- _kp_canvas_seed: random 0-255 integer
- _kp_webgl_idx: random 0-2 integer
- _kp_geo_idx: random 0-7 integer
- _kp_hw_cores: random choice of [4,6,8]
- _kp_mem: random choice of [4,8]

## Output format
Output ONLY the raw JavaScript IIFE (no markdown fences, no Python wrapper).
Start with: (function() {
End with: })();
No comments. No console.log. Strict mode: 'use strict'; at top inside IIFE.
All overrides must be idempotent (check window._kasa_privacy_applied flag, return early if already set).
"""

# ── REVIEW PROMPT ─────────────────────────────────────────────────────────────
REVIEW_PROMPT_TPL = """You are reviewing a JavaScript privacy decoy IIFE for the KASA browser.
It runs via pywebview evaluate_js after each page load.

CHECKLIST (verify each item — if broken, fix it in your output):
1. Starts with (function() { 'use strict'; and ends with })();
2. Checks window._kasa_privacy_applied at start, sets it to true, returns early if already set
3. sessionStorage seeds (_kp_canvas_seed, _kp_webgl_idx, _kp_geo_idx, _kp_hw_cores, _kp_mem) initialized if absent
4. navigator.geolocation.getCurrentPosition AND watchPosition both overridden
5. geo coords picked from sessionStorage seed index + noise, accuracy randomized
6. HTMLCanvasElement.prototype.toDataURL overridden — XOR pixel noise applied
7. CanvasRenderingContext2D.prototype.getImageData overridden — XOR pixel noise applied
8. WebGLRenderingContext.prototype.getParameter overridden — RENDERER+VENDOR spoofed, others pass-through
9. navigator.hardwareConcurrency, deviceMemory, languages, language, platform all overridden via Object.defineProperty (writable:false, configurable:false)
10. screen.width/height/availWidth/availHeight/colorDepth/pixelDepth overridden
11. Intl.DateTimeFormat prototype patched to inject Europe/Berlin timeZone
12. Date.prototype.getTimezoneOffset returns -60
13. Cookie poisoning: reads document.cookie, finds tracker patterns, writes poisoned values back
14. No console.log, no alerts, no external requests
15. All try/catch around each override section (some properties may be non-configurable on some pages)

The code to review:
```javascript
{DRAFT}
```

Output ONLY the corrected/improved raw JavaScript IIFE (no markdown, no explanation).
Start with: (function() {
End with: })();
"""

# ── PIPELINE ──────────────────────────────────────────────────────────────────
def run():
    # 1. Taslak
    draft_raw = call_model(DRAFTER, DRAFT_PROMPT, "DRAFT — privacy decoy JS")
    draft_js  = extract_js(draft_raw)

    # 2. Inceleme
    review_prompt = REVIEW_PROMPT_TPL.replace("{DRAFT}", draft_js)
    reviewed_raw  = call_model(REVIEWER, review_prompt, "REVIEW — privacy decoy JS")
    final_js      = extract_js(reviewed_raw)

    # 3. Mevcut dosyayi yedekle
    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.replace(".py", f"_bak_{ts}.py")
    shutil.copy2(TARGET, bak)
    print(f"\n[ORCH] Yedek: {bak}")

    # 4. Mevcut dosyayi oku
    with open(TARGET, encoding="utf-8") as f:
        src = f.read()

    # 5. _PRIVACY_JS sabitini ekle (henuz yoksa)
    PRIVACY_CONST = f'\n_PRIVACY_JS = r"""\n{final_js}\n"""\n'

    if "_PRIVACY_JS" in src:
        # Mevcut sabiti guncelle
        src = re.sub(
            r"_PRIVACY_JS\s*=\s*r?\"\"\"[\s\S]*?\"\"\"",
            f'_PRIVACY_JS = r"""\n{final_js}\n"""',
            src
        )
        print("[ORCH] _PRIVACY_JS guncellendi.")
    else:
        # _INGEST_JS'den once ekle
        insert_before = "_INGEST_JS"
        pos = src.find(insert_before)
        if pos == -1:
            # Dosya sonuna ekle (fallback)
            src = src + PRIVACY_CONST
        else:
            src = src[:pos] + PRIVACY_CONST + "\n" + src[pos:]
        print("[ORCH] _PRIVACY_JS eklendi.")

    # 6. on_loaded() icerisine enjeksiyon satiri ekle (yoksa)
    INJECT_LINE = "        win.evaluate_js(_PRIVACY_JS)"
    if "_PRIVACY_JS" not in src or INJECT_LINE not in src:
        # win.evaluate_js(_TOOLBAR_JS) satirindan once ekle
        src = src.replace(
            "        win.evaluate_js(_TOOLBAR_JS)",
            f"{INJECT_LINE}\n        win.evaluate_js(_TOOLBAR_JS)"
        )
        print("[ORCH] on_loaded() enjeksiyonu eklendi.")

    # 7. Yaz
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(src)

    # 8. Syntax kontrolu
    try:
        py_compile.compile(TARGET, doraise=True)
        print("[ORCH] Syntax OK.")
    except py_compile.PyCompileError as e:
        print(f"[ORCH] HATA: Syntax hatasi — {e}")
        shutil.copy2(bak, TARGET)
        print("[ORCH] Geri yuklendi (yedek).")
        sys.exit(1)

    print(f"\n[ORCH] TAMAMLANDI -> {TARGET}")

if __name__ == "__main__":
    run()
