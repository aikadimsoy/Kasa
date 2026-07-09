# -*- coding: utf-8 -*-
"""EFF Cover Your Tracks yakalama + analiz -- tamamen yerel modellerle.
Claude sadece bu emri gonderir ve sonucu okur; tanı/duzeltme/analiz deepseek+qwen'den gelir."""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "_orch", "loop"))
from model_pipe import call_model, extract_python, DRAFTER, REVIEWER  # noqa: E402

CAPTURE_SCRIPT = os.path.join(HERE, "run_eff_capture.py")
OUT = os.path.join(HERE, "eff_capture.txt")
REPORT = os.path.join(HERE, "EFF_REPORT.md")
PY = "C:/Users/REDACTED-USER/AppData/Local/Python/pythoncore-3.14-64/python.exe"


def run_capture():
    if os.path.exists(OUT):
        os.remove(OUT)
    subprocess.run([PY, CAPTURE_SCRIPT], cwd=REPO, timeout=90)
    size = os.path.getsize(OUT) if os.path.exists(OUT) else 0
    text = open(OUT, encoding="utf-8", errors="replace").read() if os.path.exists(OUT) else ""
    return size, text


def fix_capture(prev_text, symptom):
    with open(CAPTURE_SCRIPT, encoding="utf-8") as f:
        cur = f.read()
    spec = (
        "This Python script launches a pywebview browser window pointed at "
        "https://coveryourtracks.eff.org/ (via env var KASA_HEALTHCHECK_URL) and, after a fixed "
        "sleep (KASA_HEALTHCHECK_MS), captures page text via win.evaluate_js(JS) into KASA_CAPTURE_OUT, "
        "where JS defaults to 'document.body.textContent' (settable via KASA_CAPTURE_JS env var).\n\n"
        f"SYMPTOM: {symptom}\n\n"
        "The EFF site auto-runs its fingerprint test client-side on load and then shows/redirects to a "
        "results page; a single fixed-delay snapshot may fire too early, too late, or before the SPA "
        "has rendered text into the DOM.\n\n"
        "Fix run_eff_capture.py so the capture reliably gets the final results-page text:\n"
        "- Increase KASA_HEALTHCHECK_MS to a generous value (e.g. 35000-45000ms) to give the test time to finish.\n"
        "- Set KASA_CAPTURE_JS to a JS EXPRESSION (not multi-line function; evaluate_js expects a single "
        "expression it can return) that defensively returns whatever text is available even if the page is "
        "still loading, e.g. falls back through document.body ? document.body.innerText : '' style ternaries, "
        "and includes location.href in the output so we can tell what page it actually captured.\n"
        "- Keep everything else (env vars, subprocess call, timeout=60) working the same way.\n"
        "- Output the COMPLETE corrected run_eff_capture.py file.\n\n"
        f"=== CURRENT FILE ===\n```python\n{cur}\n```\n"
    )
    checklist = (
        "- Must still set KASA_HEALTHCHECK_URL to https://coveryourtracks.eff.org/\n"
        "- Must still write to eff_capture.txt via KASA_CAPTURE_OUT\n"
        "- KASA_CAPTURE_JS must be a single JS expression string (no top-level statements/semicolons that "
        "would break evaluate_js), must include location.href somewhere in the returned string\n"
        "- KASA_HEALTHCHECK_MS must be raised to at least 30000\n"
        "- Must remain valid Python (py_compile clean)\n"
    )
    draft = call_model(DRAFTER, spec, num_predict=2000)
    code = extract_python(draft)
    review = call_model(REVIEWER,
        "Review and fix against this checklist, output ONLY the complete corrected file in one "
        "```python``` block:\n\n" + checklist + "\n\n```python\n" + code + "\n```", num_predict=2000)
    return extract_python(review)


def analyze(text):
    prompt = (
        "The following is raw captured text (textContent) from a browser window that visited "
        "coveryourtracks.eff.org to test a privacy browser called KASA for tracker-blocking and "
        "fingerprinting protection. Read it and produce a concise Markdown report answering:\n"
        "1. Which page/state was actually captured (home page mid-test, or final results page)?\n"
        "2. What test categories does the captured content mention (tracking protection, ad blocking, "
        "fingerprinting protection, browser uniqueness bits, specific fingerprint vectors)?\n"
        "3. For each category found, what result/verdict is shown for this browser (protected/unique/leaked)?\n"
        "4. Any concrete leaked values visible (user agent, canvas/webgl hash, fonts, screen size, timezone, etc).\n"
        "5. If the capture looks incomplete or wrong (e.g. still on homepage, empty), say so explicitly.\n\n"
        "=== CAPTURED TEXT ===\n" + text[:15000]
    )
    return call_model(REVIEWER, prompt, num_predict=2000)


def main():
    size, text = run_capture()
    print("capture #1 size:", size)
    attempts = [{"size": size, "sample": text[:300]}]
    tries = 0
    while size < 200 and tries < 3:
        tries += 1
        symptom = f"Last capture was {size} bytes. Sample: {text[:300]!r}"
        fixed = fix_capture(text, symptom)
        with open(CAPTURE_SCRIPT, "w", encoding="utf-8") as f:
            f.write(fixed)
        try:
            subprocess.run([PY, "-m", "py_compile", CAPTURE_SCRIPT], check=True)
        except subprocess.CalledProcessError:
            continue  # guard: bozuk python, atla (dosya zaten yazildi, sonraki tur ustune yazacak)
        size, text = run_capture()
        print(f"capture #{tries+1} size:", size)
        attempts.append({"size": size, "sample": text[:300]})

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("# KASA vs coveryourtracks.eff.org -- Yerel Model Raporu\n\n")
        f.write(f"## Yakalama denemeleri\n\n")
        for i, a in enumerate(attempts):
            f.write(f"- Deneme {i+1}: {a['size']} byte -- `{a['sample']!r}`\n")
        f.write("\n## Yerel model analizi (qwen2.5-coder:14b)\n\n")
        if size >= 200:
            f.write(analyze(text))
        else:
            f.write("Yakalama 3 denemede de yeterli veri toplayamadi (site testi calismamis olabilir "
                     "veya sayfa yapisi beklenenden farkli). Ham veri: `eff_capture.txt`.\n")

    print("REPORT:", REPORT)


if __name__ == "__main__":
    main()
