"""
KASA Orkestrasyon — Browser Design System v0.1
deepseek-coder-v2:16b taslak -> qwen2.5-coder:14b review -> browser_window.py
"""
import json, sys, textwrap, re, os
import urllib.request

# Windows konsolunu UTF-8'e zorla
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA  = "http://localhost:11434/api/generate"
DRAFTER = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER= "qwen2.5-coder:14b"
ORCH_DIR= "d:/kasa/_orch"

def call_model(model: str, prompt: str, label: str, max_tokens: int = 8192) -> str:
    print(f"\n[ORCH] {label} ({model}) cagiriliyor...", flush=True)
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.15, "num_predict": max_tokens}
    }).encode()
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

def save(filename: str, content: str):
    os.makedirs(ORCH_DIR, exist_ok=True)
    path = f"{ORCH_DIR}/{filename}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[ORCH] Kaydedildi: {path}")

def extract_python(text: str) -> str:
    m = re.search(r"```python\s*\r?\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Kod blogu isaretsizsek ham don
    return text.strip()

# ── Mevcut browser_window.py oku ────────────────────────────────────────────
with open("d:/kasa/src/browser/browser_window.py", "r", encoding="utf-8") as f:
    CURRENT_CODE = f.read()

# ── ADIM 1: deepseek taslak ─────────────────────────────────────────────────
DRAFT_PROMPT = textwrap.dedent("""
You are an expert Python developer and UI/CSS engineer.
Rewrite the complete Python module `src/browser/browser_window.py` for **Project KASA**.
KASA is a local-first encrypted memory vault. The browser is a pywebview/Edge WebView2 window.

## EXISTING CODE (keep structure, update toolbar/CSS only)
```python
""" + CURRENT_CODE + """
```

## DESIGN SYSTEM v0.1 — HARD CONSTRAINTS (ALL must be respected)

### 1. Token Table (CSS custom properties — NO hardcoded values)
```
Colors:
  --kasa-primary:       #E02244   (brand crimson)
  --kasa-primary-hover: #C41E3D
  --kasa-accent:        #1BA7C2   (cyan)
  --kasa-n950:          #0D1017   (app bg)
  --kasa-n900:          #12161F   (panel)
  --kasa-n800:          #1A2029   (surface)
  --kasa-n700:          #242B37   (elevated)
  --kasa-n500:          #5B6472   (secondary text)
  --kasa-n300:          #9AA3B2   (dimmed)
  --kasa-n100:          #E4E7EC
  --kasa-secure:        #2FBF71   (HTTPS green)
  --kasa-warning:       #E8A13C   (mixed amber)
  --kasa-danger:        #E5484D   (HTTP/phish red)
  --kasa-private:       #8B5CF6   (private purple)

Chrome dimensions (all 8px multiples):
  --kasa-toolbar-h:     48px      (6×8)
  --kasa-bar-h:         36px      (4.5×8)
  --kasa-rail-w:        64px      (8×8)
  --kasa-panel-w:       256px     (32×8)
  --kasa-icon:          24px      (3×8)
  --kasa-touch:         48px      (6×8, min touch target)

Radius: --kasa-r-sm:8px  --kasa-r-md:12px  --kasa-r-lg:16px  --kasa-r-pill:9999px
Shadow: --kasa-e1:0 1px 2px rgba(0,0,0,.24)  --kasa-e2:0 4px 12px rgba(0,0,0,.32)
Motion: --kasa-t-micro:120ms  --kasa-t-std:200ms  --kasa-ease:cubic-bezier(0.2,0,0,1)
```

### 2. Self-hosted Fonts (served from http://localhost:8000/assets/fonts/)
```css
@font-face { font-family:'KasaUI'; font-weight:400; src:url('http://localhost:8000/assets/fonts/inter-400.woff2') format('woff2'); }
@font-face { font-family:'KasaUI'; font-weight:500; src:url('http://localhost:8000/assets/fonts/inter-500.woff2') format('woff2'); }
@font-face { font-family:'KasaUI'; font-weight:600; src:url('http://localhost:8000/assets/fonts/inter-600.woff2') format('woff2'); }
@font-face { font-family:'KasaMono'; font-weight:400; src:url('http://localhost:8000/assets/fonts/jetbrains-mono-400.woff2') format('woff2'); }
```

### 3. Security Ring (left of address bar, 24px icon)
Inline SVG shield icon. Color and icon glyph changes based on protocol:
- window.location.protocol === 'https:' → color var(--kasa-secure), checkmark inside shield
- window.location.protocol === 'http:'  → color var(--kasa-danger), X inside shield
- else                                  → color var(--kasa-warning), ! inside shield
Security ring ALWAYS shows icon + has a title attribute for accessibility.
Security ring clicks do nothing (decorative + accessible label only).

### 4. Address Bar URL Display
- Use JetBrains Mono ('KasaMono') font
- Show full URL but visually: eTLD+1 bold (font-weight:600, color:white), rest dimmed (--kasa-n300)
- Implement via: input element value = full href; ALSO create a visual overlay div that shows
  the styled URL when input is NOT focused. On focus: hide overlay, show raw input. On blur: show overlay.
- eTLD+1 extraction: split hostname by '.', take last 2 segments (simple heuristic).
- Use the input for editing (onkeydown Enter → _kasa_navigate).

### 5. Sidebar Rail (left, fixed)
- Width: 64px collapsed, 256px when expanded (transition: var(--kasa-t-std))
- Background: var(--kasa-n900)
- Shadow: var(--kasa-e2) on right edge
- Top: toggle button (hamburger ≡, 48×48, center)
- Items (icon + label when expanded):
  1. Home  — SVG house icon → navigate to 'https://lite.duckduckgo.com/lite'
  2. Vault — SVG key icon   → call window.pywebview.api.open_vault() if available
  3. Shield— SVG shield     → show tracker count badge (start at 0, text: "0 blocked")
  4. Settings — SVG gear    → placeholder, no action
- Icon area: 48×48 each, centered in 64px rail
- Labels: shown only when expanded, font-size 13px (--kasa-n300), truncate with ellipsis
- Active item highlighted: background var(--kasa-n800), left 2px var(--kasa-primary) border

### 6. Toolbar (top, 48px, fixed)
- Left edge starts at var(--kasa-rail-w) = 64px (offset sidebar)
- Right edge: 0
- Background: var(--kasa-n950)
- Box-shadow: var(--kasa-e2) below
- Content (vertically centered, gap 8px, padding 0 12px):
  - Back button ← : 48×48, border-radius var(--kasa-r-md), click → history.go(-1)
  - Fwd button →  : 48×48, border-radius var(--kasa-r-md), click → history.go(1)
  - Reload ↺     : 48×48, border-radius var(--kasa-r-md), click → location.reload()
  - Address bar container (flex:1, height 36px, border-radius 9999px, bg var(--kasa-n800), border 1px solid var(--kasa-n700), display:flex, align:center, gap:8px, padding:0 12px):
    - Security Ring (24px)
    - URL display (flex:1) — input behind, styled overlay on top
    - Status dot (8×8 circle, color changes on ingest)
  - Ingest label: 11px, var(--kasa-n500), id="_kasa_status"

### 7. URL Polling
- setInterval every 500ms: compare window.location.href to last known URL
- On change: update address bar input value, update security ring color/icon, update overlay display

### 8. body margin
- Apply margin-top: 48px and margin-left: 64px to document.body on injection
- Sidebar toggle changes margin-left between 64px (collapsed) and 256px (expanded)

### 9. Keep from existing code
- _kasa_navigate(v) — exact same logic (protocol → domain → DuckDuckGo)
- target="_blank" click interception → window.location.href = a.href
- _INGEST_JS constant — unchanged
- KasaApi class — add open_vault() method that prints to console
- open_browser() function — unchanged logic

## SVG ICONS (inline, 24×24, stroke 1.75, round cap, outline style)
Use these exact SVG paths:

Home icon:
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M3 12L12 4l9 8"/>
  <path d="M5 10v9a1 1 0 001 1h4v-5h4v5h4a1 1 0 001-1v-9"/>
</svg>

Key (Vault) icon:
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="8" cy="15" r="4"/>
  <path d="M12 15h8M18 13v4"/>
</svg>

Shield icon:
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
</svg>

Gear (Settings) icon:
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3"/>
  <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
</svg>

Security Shield — SECURE (checkmark):
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  <polyline points="9,12 11,14 15,10"/>
</svg>

Security Shield — DANGER (X):
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  <line x1="9" y1="9" x2="15" y2="15"/>
  <line x1="15" y1="9" x2="9" y2="15"/>
</svg>

Security Shield — WARNING (!):
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  <line x1="12" y1="9" x2="12" y2="13"/>
  <dot cx="12" cy="16" r="0.5" fill="currentColor"/>
</svg>

Hamburger (toggle) icon:
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round">
  <line x1="3" y1="6" x2="21" y2="6"/>
  <line x1="3" y1="12" x2="21" y2="12"/>
  <line x1="3" y1="18" x2="21" y2="18"/>
</svg>

## OUTPUT
Write ONLY the complete Python code inside a ```python ... ``` block.
The module must import: webview, urllib.request, json, threading, os
Do NOT add any explanation outside the code block.
Comments inside the code must be in Turkish.
""").strip()

draft_raw = call_model(DRAFTER, DRAFT_PROMPT, "TASLAK (browser design)", max_tokens=8192)
save("15_browser_design_draft_raw.txt", draft_raw)
draft_code = extract_python(draft_raw)
save("15_browser_design_draft_code.py", draft_code)

# ── ADIM 2: qwen2.5-coder review ────────────────────────────────────────────
REVIEW_PROMPT = textwrap.dedent(f"""
You are a senior Python and web-UI code reviewer.
Review this browser_window.py module for **Project KASA** (pywebview browser).

## Checklist
1. Are ALL CSS dimensions multiples of 8px? (toolbar=48, bar=36, rail=64, touch=48, icon=24)
2. Are CSS custom properties (--kasa-*) used consistently — NO hardcoded hex/px values outside :root?
3. Does _TOOLBAR_JS inject a <style> tag with @font-face + :root tokens BEFORE building DOM?
4. Does the security ring update on URL change (setInterval polling)?
5. Does the URL overlay correctly highlight eTLD+1 (font-weight:600) vs subdomain/path (n-300)?
6. Does sidebar have correct width transition (64px ↔ 256px)?
7. Is body margin-top=48px and margin-left=64px (rail width) applied?
8. Is _kasa_navigate logic intact (protocol → domain → DuckDuckGo)?
9. Is target="_blank" click interception intact?
10. Is _INGEST_JS present and unchanged?
11. Is KasaApi class complete with ingest(), _post(), _set_status(), set_window(), open_vault()?
12. Is open_browser() function complete with new_window_requested handler?
13. Are Python imports correct (webview, urllib.request, json, threading, os)?
14. Any JavaScript syntax errors you can spot?

## Draft Code
```python
{draft_code[:10000]}
```

Output a corrected, complete ```python ... ``` block.
If no changes needed, output the original unchanged inside the block.
After the block write a concise Turkish summary of ALL changes made.
""").strip()

review_raw = call_model(REVIEWER, REVIEW_PROMPT, "REVIEW (browser design)", max_tokens=8192)
save("15_browser_design_review_raw.txt", review_raw)
final_code = extract_python(review_raw)
save("15_browser_design_final_code.py", final_code)

# ── ADIM 3: Uygula ──────────────────────────────────────────────────────────
if len(final_code) < 500:
    print("[ORCH] HATA: Cikti cok kisa, uygulama iptal!")
    sys.exit(1)

TARGET = "d:/kasa/src/browser/browser_window.py"
# Yedeği al
import shutil, datetime
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy(TARGET, TARGET + f".bak.{ts}")
print(f"[ORCH] Yedek: {TARGET}.bak.{ts}")

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(final_code)
print(f"[ORCH] Yazildi: {TARGET}")

# ── ADIM 4: Syntax check ────────────────────────────────────────────────────
import py_compile
try:
    py_compile.compile(TARGET, doraise=True)
    print("[ORCH] py_compile: GECTI")
except py_compile.PyCompileError as e:
    print(f"[ORCH] py_compile HATA: {e}")
    print("[ORCH] Yedekten geri yukle...")
    shutil.copy(TARGET + f".bak.{ts}", TARGET)
    sys.exit(1)

print("\n[ORCH] Pipeline tamamlandi — browser_window.py guncellendi.")
