"""
KASA Orkestrasyon — Sira 0: Gizlilik Seviyesi Kaliciligi v1.0
deepseek taslak -> qwen review. Cikti: 23_level_python.py
  -> Claude dogrulayip browser_window.py'ye splice eder (KasaApi metodlari + prelude helper).

Sorun: seviye origin-scoped localStorage._kasa_privacy_level'de -> domain-arasi kalmiyor.
Cozum: seviyeyi Python tarafinda browser_config.json'a al; her navigasyonda
window.__KASA_LEVEL__ ile enjekte et. _PRIVACY_JS bunu localStorage'dan ONCE okur.
Not: config zaten proxy anahtarlari tutuyor -> set_level MERGE yapmali (ezmemeli).
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

def extract_py(text):
    m = re.search(r"```(?:python)?\n([\s\S]+?)```", text)
    return m.group(1).strip() if m else text.strip()

DRAFT = r'''Write Python code for a pywebview app. Context already exists in the module:
- import os, json
- _BROWSER_CONFIG_PATH = "d:/kasa/browser_config.json"
- def _read_browser_config(): returns a dict (may already contain "proxy_enabled",
  "proxy_address"); returns {"proxy_enabled": False, "proxy_address": ""} on error.
- class KasaApi exists.

The privacy level is one of: "off", "standard", "strict", "paranoid" (default "strict").

Write EXACTLY these three things (nothing else):

1) A module-level function `_level_prelude_js()`:
   - cfg = _read_browser_config()
   - lvl = cfg.get("privacy_level") or "strict"
   - if lvl not in ("off","standard","strict","paranoid"): lvl = "strict"
   - return the JS string:  'window.__KASA_LEVEL__=' + json.dumps(lvl) + ';'
     (use json.dumps so the value is safely quoted)

2) A method for class KasaApi (4-space indent, standalone so I can paste it in):
   def get_level(self):
       return _read_browser_config().get("privacy_level") or "strict"

3) A method for class KasaApi (4-space indent):
   def set_level(self, level):
       - allowed = ("off","standard","strict","paranoid")
       - lvl = level if level in allowed else "strict"
       - cfg = _read_browser_config()          # READ existing (MERGE, do not overwrite proxy keys)
       - cfg["privacy_level"] = lvl
       - try: write cfg to _BROWSER_CONFIG_PATH via json.dump; return lvl
       - except Exception as e: print("[KASA] set_level hata:", str(e)); return "strict"

CRITICAL: set_level MUST read the existing config first and merge (preserve proxy_enabled /
proxy_address). Do NOT write a fresh dict with only privacy_level.
Output ONLY one python code block.'''

REVIEW = ('Review this Python. Verify: (1) _level_prelude_js() reads config, validates level '
    'against the 4 allowed values defaulting to "strict", returns '
    "'window.__KASA_LEVEL__=' + json.dumps(lvl) + ';'; (2) get_level returns "
    'config privacy_level or "strict"; (3) set_level validates level, READS existing config '
    'and MERGES (preserves proxy_enabled/proxy_address) before writing, try/except returns '
    '"strict" on error, returns the level on success; all KasaApi methods 4-space indent. '
    'The most important check: set_level must NOT overwrite the whole file with only '
    'privacy_level. Fix bugs. Output ONLY the corrected python code block.\n\n'
    '```python\n{DRAFT}\n```')

def run():
    draft = extract_py(call_model(DRAFTER, DRAFT, "DRAFT — level python"))
    final = extract_py(call_model(REVIEWER, REVIEW.replace("{DRAFT}", draft), "REVIEW — level python"))
    with open("d:/kasa/_orch/23_level_python.py", "w", encoding="utf-8") as f:
        f.write(final + "\n")
    print("\n[ORCH] yazildi -> 23_level_python.py")
    print("[ORCH] Claude dogrulayip browser_window.py'ye splice edecek.")

if __name__ == "__main__":
    run()
