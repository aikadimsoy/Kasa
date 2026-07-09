"""
KASA Orkestrasyon — Browser Sidebar (acilir-kapanir sol menu) v1.0
deepseek-coder-v2:16b taslak -> qwen2.5-coder:14b review
Cikti: browser_window.py icine _SIDEBAR_JS sabiti + on_loaded() enjeksiyonu

Sidebar bolumleri:
  - Araclar (Tools)
  - Kullanici Ayarlari (User settings)
  - Gizlilik Seviyesi (Privacy level) -> localStorage._kasa_privacy_level
"""
import json, sys, re, shutil, datetime, py_compile
import urllib.request

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
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": 0.15, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
                                 headers={"Content-Type": "application/json"})
    out = []
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                tok = obj.get("response", "")
                out.append(tok)
                print(tok, end="", flush=True)
                if obj.get("done"):
                    break
            except json.JSONDecodeError:
                continue
    print()
    return "".join(out)

def extract_js(text: str) -> str:
    m = re.search(r"```(?:javascript|js)?\n([\s\S]+?)```", text)
    return m.group(1).strip() if m else text.strip()

# ── DRAFT PROMPT ──────────────────────────────────────────────────────────────
DRAFT_PROMPT = r"""You are writing a JavaScript IIFE injected into every page of the KASA browser
(via pywebview evaluate_js, after page load). A fixed top toolbar of height 48px
already exists (#_kasa_toolbar). CSS design tokens are already defined on :root:
--kasa-n950 #0D1017, --kasa-n900 #12161F, --kasa-n800 #1A2029, --kasa-n700 #242B37,
--kasa-n500 #5B6472, --kasa-n300 #9AA3B2, --kasa-n100 #E4E7EC,
--kasa-primary #E02244, --kasa-accent #1BA7C2, --kasa-secure #2FBF71,
--kasa-warning #E8A13C, --kasa-danger #E5484D, --kasa-private #8B5CF6,
--kasa-e2 (shadow), --kasa-t-std 200ms, --kasa-ease cubic-bezier(0.2,0,0,1).
Fonts: KasaUI (sans), KasaMono (mono).

Write ONE JavaScript IIFE `_SIDEBAR_JS` that builds a COLLAPSIBLE LEFT DRAWER menu.

## Structure
1. Idempotent: if document.getElementById('_kasa_rail') exists, return immediately.
2. A thin vertical RAIL fixed to the left edge, below the toolbar:
   position:fixed; top:48px; left:0; bottom:0; width:56px; background:var(--kasa-n900);
   z-index:2147483646; display:flex; flex-direction:column; align-items:center;
   gap:8px; padding-top:12px; box-shadow:var(--kasa-e2).
   The rail is ALWAYS visible. It holds icon buttons (48x48, border-radius:12px,
   color:var(--kasa-n300), transparent bg, hover bg var(--kasa-n800)):
     - Hamburger toggle button (top) -> toggles the expanded PANEL
     - Araclar (tools) icon button
     - Kullanici (user) icon button
     - Gizlilik (shield) icon button
3. An expanded PANEL that slides out to the right of the rail:
   position:fixed; top:48px; left:56px; bottom:0; width:256px; background:var(--kasa-n950);
   z-index:2147483646; box-shadow:var(--kasa-e2); overflow-y:auto; padding:16px;
   color:var(--kasa-n100); font-family:KasaUI,sans-serif; font-size:14px;
   transform:translateX(-320px); transition:transform var(--kasa-t-std) var(--kasa-ease);
   When open, transform:translateX(0). Track open state with a JS variable.
   Clicking a rail icon button opens the panel and shows that section; clicking the
   hamburger toggles open/closed.

## Panel sections (show one at a time via a switchSection(name) function)
### Section "araclar" (Araclar / Tools)
   Heading "Araclar". A list of tool toggle rows. Each row: label + a toggle switch.
   Tools: "Ekran goruntusu", "Sayfa metnini kaydet", "Cerez goruntule", "Vault'a gonder".
   Toggle state saved to localStorage keys: _kasa_tool_screenshot, _kasa_tool_savetext,
   _kasa_tool_cookies, _kasa_tool_vault. Default all true except screenshot false.

### Section "kullanici" (Kullanici Ayarlari / User settings)
   Heading "Kullanici Ayarlari". Fields:
   - Text input "Takma ad" -> localStorage _kasa_user_alias
   - Select "Arama motoru" options: DuckDuckGo, Startpage, Brave -> localStorage _kasa_user_search
   - Select "Tema" options: Koyu, Sistem -> localStorage _kasa_user_theme (default Koyu)
   Each change writes to localStorage immediately.

### Section "gizlilik" (Gizlilik Seviyesi / Privacy level) — MOST IMPORTANT
   Heading "Gizlilik Seviyesi". Four mutually-exclusive level cards (radio behavior),
   stored in localStorage._kasa_privacy_level (values: off, standard, strict, paranoid;
   default strict). Each card shows a title + short description:
   - "Kapali" (off): "Hicbir sahte veri yok. Gercek parmak izin gonderilir."
   - "Standart" (standard): "Konum, dil, saat dilimi, ekran sahte. Canvas/WebGL dokunulmaz."
   - "Siki" (strict): "Standart + Canvas/WebGL parmak izi zehirleme + tracker cerez zehirleme."
   - "Paranoyak" (paranoid): "Siki + bilinen tracker istekleri engellenir (deneysel)."
   The currently-selected card has border:2px solid var(--kasa-primary); others
   border:1px solid var(--kasa-n700). Clicking a card:
     localStorage.setItem('_kasa_privacy_level', value);
     then re-render selection highlight;
     then show a small note "Degisiklik icin sayfayi yenile" and a Reload button
     (location.reload()).

## General rules
- No external requests, no console.log.
- Push page content right so the rail does not cover it:
  document.body.style.marginLeft = '56px';  (in addition to existing marginTop)
- Use inline SVG (stroke=currentColor, stroke-width 1.75, 20x20) for the 4 rail icons.
- Wrap risky DOM ops in try/catch.
- Output ONLY the raw JS IIFE. Start with (function(){ and end with })();
- No markdown fences in the actual code.
"""

# ── REVIEW PROMPT ─────────────────────────────────────────────────────────────
REVIEW_PROMPT_TPL = r"""You are reviewing a JavaScript IIFE (_SIDEBAR_JS) for the KASA browser.
It injects a collapsible left drawer with three sections.

CHECKLIST — verify each, FIX in your output if broken:
1. Idempotent: returns early if #_kasa_rail already exists.
2. Rail: fixed, top:48px, left:0, width:56px, always visible, 4 icon buttons (hamburger, tools, user, shield).
3. Panel: fixed, left:56px, width:256px, slides via transform translateX, transition uses --kasa-t-std.
4. switchSection(name) shows exactly one of: araclar, kullanici, gizlilik.
5. Section "araclar": 4 tool toggles bound to localStorage (_kasa_tool_screenshot/savetext/cookies/vault).
6. Section "kullanici": alias input, search select, theme select -> localStorage on change.
7. Section "gizlilik": 4 cards (off/standard/strict/paranoid) radio behavior; writes localStorage._kasa_privacy_level; selected card highlighted with primary border; Reload button present.
8. document.body.style.marginLeft = '56px' set.
9. All var()/token colors reference existing --kasa-* variables. No undefined CSS vars.
10. Inline SVG icons valid, stroke=currentColor.
11. No external requests, no console.log, no alert.
12. try/catch around DOM insertion.
13. Valid JS: no undeclared identifiers, balanced braces, ends with })();
14. Event handlers use addEventListener or onclick strings that reference only in-scope/global functions (make handlers closures, not string-based references to local functions).

Code to review:
```javascript
{DRAFT}
```

Output ONLY the corrected raw JS IIFE. Start with (function(){ and end with })();  No markdown, no prose.
"""

def run():
    draft = extract_js(call_model(DRAFTER, DRAFT_PROMPT, "DRAFT — sidebar JS"))
    review_prompt = REVIEW_PROMPT_TPL.replace("{DRAFT}", draft)
    final_js = extract_js(call_model(REVIEWER, review_prompt, "REVIEW — sidebar JS"))

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = TARGET.replace(".py", f"_bak_{ts}.py")
    shutil.copy2(TARGET, bak)
    print(f"\n[ORCH] Yedek: {bak}")

    with open(TARGET, encoding="utf-8") as f:
        src = f.read()

    if "_SIDEBAR_JS" in src:
        src = re.sub(r'_SIDEBAR_JS\s*=\s*r?"""[\s\S]*?"""',
                     f'_SIDEBAR_JS = r"""\n{final_js}\n"""', src)
        print("[ORCH] _SIDEBAR_JS guncellendi.")
    else:
        anchor = "_INGEST_JS"
        pos = src.find(anchor)
        const = f'\n_SIDEBAR_JS = r"""\n{final_js}\n"""\n\n'
        src = src[:pos] + const + src[pos:] if pos != -1 else src + const
        print("[ORCH] _SIDEBAR_JS eklendi.")

    inject = "        win.evaluate_js(_SIDEBAR_JS)"
    if inject not in src:
        src = src.replace("        win.evaluate_js(_INGEST_JS)",
                          f"{inject}\n        win.evaluate_js(_INGEST_JS)")
        print("[ORCH] on_loaded() enjeksiyonu eklendi.")

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(src)

    try:
        py_compile.compile(TARGET, doraise=True)
        print("[ORCH] Syntax OK.")
    except py_compile.PyCompileError as e:
        print(f"[ORCH] HATA: {e}")
        shutil.copy2(bak, TARGET)
        print("[ORCH] Geri yuklendi.")
        sys.exit(1)

    print(f"\n[ORCH] TAMAMLANDI -> {TARGET}")

if __name__ == "__main__":
    run()
