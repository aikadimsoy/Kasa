"""
Pipeline 11 — V0.2 Chrome Extension iskelet
deepseek taslak → qwen review → d:/kasa/browser_extension/
4 dosya: manifest.json, content.js, background.js, popup.html+popup.js
"""
import json, re, os, sys
import urllib.request

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
ORCH     = "d:/kasa/_orch"
OUT_DIR  = "d:/kasa/browser_extension"

def call_model(model, prompt, label):
    print(f"\n[ORCH] {label} ({model})...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": 0.1, "num_predict": 6000}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
                                  headers={"Content-Type": "application/json"})
    buf = []
    with urllib.request.urlopen(req, timeout=360) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line: continue
            try:
                obj = json.loads(line)
                tok = obj.get("response", "")
                buf.append(tok); print(tok, end="", flush=True)
                if obj.get("done"): break
            except: continue
    print(); return "".join(buf)

def extract_block(text, lang):
    m = re.search(rf"```{lang}\s*\r?\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else None

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[ORCH] Yazildi: {path}")

# ── ADIM 1: deepseek — manifest + content + background ──
DRAFT_PROMPT = """
Write a **Manifest V3 Chrome Extension** for Project KASA.

## Purpose
Read-only: captures current page title + URL + text summary, sends to local KASA MCP server via fetch().

## Exact MCP endpoint
POST http://localhost:8000/v1/execute_tool
Content-Type: application/json
Body:
{
  "tool": "event_ingest",
  "agent_id": "browser_extension",
  "params": {
    "source": "chrome_extension",
    "type": "page_visit",
    "content": {
      "url": "<current_page_url>",
      "title": "<page_title>",
      "summary": "<first 500 chars of body text, whitespace-collapsed>"
    },
    "ttl_days": 30
  }
}

## Files to generate

### FILE 1: manifest.json
- manifest_version: 3
- name: "KASA Memory"
- version: "0.2.0"
- description: "Local memory vault connector"
- permissions: ["activeTab", "storage"]
- host_permissions: ["http://localhost:8000/*"]
- content_scripts: runs content.js on all URLs (document_idle)
- background: service_worker = background.js
- action: popup.html
- icons: (leave empty object {})

### FILE 2: content.js (content script)
- Extracts: document.title, location.href, first 500 chars of document.body.innerText (collapse whitespace)
- Sends message to background: chrome.runtime.sendMessage({type:"PAGE_VISIT", data:{url, title, summary}})
- Do NOT fetch() directly from content script (CORS)
- Runs only if page is http or https

### FILE 3: background.js (service worker)
- Listens for chrome.runtime.onMessage
- On message type "PAGE_VISIT": POST to http://localhost:8000/v1/execute_tool with the exact body above
- On fetch error: console.warn("KASA: MCP unreachable", err) — silent fail
- No retries

### FILE 4: popup.html + popup.js (inline in one html file)
- Simple HTML: title "KASA Memory", one status line showing "MCP: connected" or "MCP: offline"
- On load: fetch("http://localhost:8000/") → if 200 show connected, else offline
- Minimal inline CSS: dark background #1a1a2e, white text, monospace font
- All JS inline in <script> tag

Output each file in a separate fenced block labeled:
```json  ← for manifest.json
```javascript  ← for content.js
```javascript  ← for background.js
```html  ← for popup.html

Output in EXACTLY that order. No explanations between blocks.
""".strip()

draft_raw = call_model(DRAFTER, DRAFT_PROMPT, "EXT TASLAK")
with open(f"{ORCH}/11_ext_draft_raw.txt", "w", encoding="utf-8") as f:
    f.write(draft_raw)

# ── ADIM 2: qwen review ──
REVIEW_PROMPT = f"""
Review this Chrome Extension (Manifest V3) for Project KASA browser extension.
Fix any issues and output the corrected files.

## Checklist
1. manifest.json: manifest_version=3, has content_scripts, background.service_worker, action.default_popup, host_permissions includes localhost:8000
2. content.js: uses chrome.runtime.sendMessage (NOT fetch directly), extracts title+url+summary(500 chars)
3. background.js: listens onMessage, fetches POST to http://localhost:8000/v1/execute_tool with correct body structure, silent fail on error
4. popup.html: checks http://localhost:8000/ for health, shows connected/offline, all JS inline

## Draft output:
{draft_raw[:8000]}

Output each corrected file in a separate fenced block:
```json        ← manifest.json
```javascript  ← content.js
```javascript  ← background.js
```html        ← popup.html

EXACTLY that order. No text between blocks.
""".strip()

review_raw = call_model(REVIEWER, REVIEW_PROMPT, "EXT REVIEW")
with open(f"{ORCH}/11_ext_review_raw.txt", "w", encoding="utf-8") as f:
    f.write(review_raw)

# ── ADIM 3: JSON ve JS bloklarını çıkar ve yaz ──
# manifest.json
json_blocks = re.findall(r"```json\s*\r?\n(.*?)```", review_raw, re.DOTALL)
js_blocks   = re.findall(r"```javascript\s*\r?\n(.*?)```", review_raw, re.DOTALL)
html_blocks = re.findall(r"```html\s*\r?\n(.*?)```", review_raw, re.DOTALL)

if not json_blocks:
    print("[ORCH] HATA: manifest.json bulunamadi — draft'tan aliyor")
    json_blocks = re.findall(r"```json\s*\r?\n(.*?)```", draft_raw, re.DOTALL)

if not js_blocks or len(js_blocks) < 2:
    print("[ORCH] HATA: JS blokları eksik — draft'tan tamamlıyor")
    js_blocks = re.findall(r"```javascript\s*\r?\n(.*?)```", draft_raw, re.DOTALL)

if not html_blocks:
    print("[ORCH] HATA: popup.html bulunamadi — draft'tan aliyor")
    html_blocks = re.findall(r"```html\s*\r?\n(.*?)```", draft_raw, re.DOTALL)

errors = []
if json_blocks:
    try:
        json.loads(json_blocks[0])
        write_file(f"{OUT_DIR}/manifest.json", json_blocks[0].strip())
    except json.JSONDecodeError as e:
        errors.append(f"manifest.json gecersiz JSON: {e}")
        print(f"[ORCH] HATA: {errors[-1]}")
else:
    errors.append("manifest.json blogu bulunamadi")

if js_blocks:
    write_file(f"{OUT_DIR}/content.js", js_blocks[0].strip())
    if len(js_blocks) >= 2:
        write_file(f"{OUT_DIR}/background.js", js_blocks[1].strip())
    else:
        errors.append("background.js blogu bulunamadi")
else:
    errors.append("JS bloklari bulunamadi")

if html_blocks:
    write_file(f"{OUT_DIR}/popup.html", html_blocks[0].strip())
else:
    errors.append("popup.html blogu bulunamadi")

print("\n[ORCH] ── SONUC ──")
if errors:
    for e in errors:
        print(f"  [!] {e}")
    sys.exit(1)
else:
    print(f"  [OK] 4 dosya yazildi → {OUT_DIR}/")
    print("  [OK] Pipeline 11 tamamlandi.")
    print("\n  Sonraki adim:")
    print("  1. Chrome > chrome://extensions/ > Developer mode ON")
    print(f"  2. 'Load unpacked' > {OUT_DIR}")
    print("  3. run.py ile MCP sunucuyu baslat: python run.py")
    print("  4. Herhangi bir sayfaya git → KASA'da event_ingest tetiklenir")
