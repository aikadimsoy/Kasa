# -*- coding: utf-8 -*-
"""
KASA Red-Team — AI Atak Test araci icin KIMLIK-DOGRULAMA modulu ureticisi (sifir-token)
deepseek taslak -> qwen inceleme -> py_compile -> redteam/aitest_auth.py
Uretilen modul: salted-scrypt ile parola saklar/dogrular (parola ASLA duz metin degil).
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
Write a SINGLE self-contained Python 3 file `aitest_auth.py`, STANDARD LIBRARY ONLY
(argparse, json, os, sys, hashlib, hmac, secrets). It provides password-protected authorization
for the AI attack-test tool. Passwords are NEVER stored in plaintext — only a salted scrypt hash.

=== FUNCTIONS ===
def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)

def provision(username: str, password: str, path: str = "ai_test_auth.json") -> None:
    # salt = os.urandom(16); compute hash; write json:
    # {"username":username, "salt":salt.hex(), "hash":_hash(...).hex(), "algo":"scrypt",
    #  "n":16384, "r":8, "p":1}. Overwrite path.

def verify(username: str, password: str, path: str = "ai_test_auth.json") -> bool:
    # If path missing -> return False. Load json. If username != stored username -> False.
    # Recompute hash from stored salt (bytes.fromhex) and compare with hmac.compare_digest
    # against bytes.fromhex(stored hash). Return bool. Never raise -> wrap in try/except -> False.

=== CLI (argparse subcommands) ===
  set   --user U [--password P]
        If --password omitted, GENERATE a strong one: secrets.token_urlsafe(12). Call provision(...).
        Then print EXACTLY (so it can be shared once):
           "USERNAME: <U>"
           "PASSWORD: <P>"
           "STORED  : ai_test_auth.json (salted scrypt; parola duz metin saklanmadi)"
  check --user U --password P
        print "OK" and exit 0 if verify() True, else print "FAIL" and exit 1.
Add Turkish comments. Output ONLY one ```python``` block.
'''

CHECK = r'''
1. Uses hashlib.scrypt(n=2**14,r=8,p=1,dklen=32); salt=os.urandom(16); hex-encoded in json.
2. verify() returns False (never raises) on missing file / bad json / wrong username / wrong pass;
   uses hmac.compare_digest for constant-time compare.
3. `set` generates secrets.token_urlsafe(12) when --password omitted and prints USERNAME/PASSWORD lines.
4. `check` prints OK/FAIL and sets exit code 0/1.
5. No plaintext password stored anywhere. Valid Python 3, stdlib only.
'''

def call_model(model, prompt, label, num_predict=3000, temp=0.15):
    print(f"\n[AUTH] {label} ({model}) ...", flush=True)
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
    print(f"[AUTH] yazildi: {path}")

def main():
    draft = call_model(DRAFTER, "Generate exactly as specified.\n\n" + SPEC, "TASLAK")
    save(os.path.join(HERE, "aitest_auth_draft.txt"), draft)
    code = extract_python(draft)
    review = call_model(REVIEWER,
        "Review and FIX against the checklist. Output ONLY the corrected file in one ```python``` block.\n\n"
        "=== CHECKLIST ===\n" + CHECK + "\n\n=== DRAFT ===\n```python\n" + code[:8000] + "\n```", "REVIEW")
    save(os.path.join(HERE, "aitest_auth_review.txt"), review)
    final = extract_python(review)
    out = os.path.join(HERE, "aitest_auth.py")
    save(out, final)
    try:
        py_compile.compile(out, doraise=True)
        print("[AUTH] py_compile: GECTI")
    except py_compile.PyCompileError as e:
        print(f"[AUTH] py_compile HATA:\n{e}"); sys.exit(1)

if __name__ == "__main__":
    main()
