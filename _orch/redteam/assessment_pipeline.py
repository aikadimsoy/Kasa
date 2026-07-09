# -*- coding: utf-8 -*-
"""
KASA Red-Team — KONSOLIDE DEGERLENDIRME raporu (sifir-token) v1.0
hermes3:8b yazar -> qwen2.5-coder:14b inceler. Cikti: redteam/REDTEAM_ASSESSMENT.md
Model YALNIZ asagidaki DOGRULANMIS bulgulari kullanir (Claude canli deneylerden topladi).
Rapor English (govde) + Turkce ozet satirlari.
"""
import json, sys, os, urllib.request

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA   = "http://localhost:11434/api/generate"
WRITER   = "hermes3:8b"
REVIEWER = "qwen2.5-coder:14b"
HERE     = os.path.dirname(os.path.abspath(__file__))

FINDINGS = r'''
KASA RED-TEAM CAMPAIGN — VERIFIED FINDINGS (all from LIVE experiments on the user's own machine).
Scope: authorized defensive security evaluation. Two targets: (1) MCP vault server on 127.0.0.1:8000,
(2) anti-fingerprint WebView2 browser. Zero-token: local models generated all attack/test code.

== TRACK A — Vault core pytest (Layer 1 smoke) ==
- Built tests/conftest.py + tests/test_smoke.py via deepseek->qwen. Result: 8/8 PASS.
- Proven up: 4-table schema, event write/read, health endpoint, end-to-end authorized ingest,
  no-token rejection, audit log written, run.py wiring. Core is "alive & not crashing".
- 3 bugs hit during generation were TEST-HARNESS bugs (model inconsistency across two files),
  NOT KASA code bugs; spliced.

== TRACK B — Browser identity leak (external adversary fingerprint site) ==
Method: a local "malicious" site captured how the browser looks from OUTSIDE, over TWO page loads.
Browser was in PARANOID privacy level (spoofing fully enabled). Key comparison:
  PASS 1 (first page of a session, BEFORE pre-injection applies — race):
    language=tr, languages=[tr], screen=3440x1440, hwConcurrency=16, deviceMemory=32,
    webglRenderer="NVIDIA RTX 5070", timezone=Europe/Berlin, canvasHash=2475da68,
    webrtc=2x "typ host" (mDNS .local).  => 100% REAL identity leaked.
  PASS 2 (second navigation, pre-injection active):
    language=de-DE, languages=[de-DE,de,en-US,en], screen=1920x1080, hwConcurrency=8,
    deviceMemory=4, canvasHash=4830c5c8 (CHANGED => canvas poison works), webrtc=[] (filter works),
    BUT webglRenderer STILL "NVIDIA RTX 5070", timezone still Europe/Berlin with tzOffset=-60.
  On BOTH passes: HTTP Accept-Language header = "tr"; sec-ch-ua reveals "Microsoft Edge WebView2".
FOUR CONFIRMED GAPS:
  B1 [CRITICAL] First-load race: the FIRST page a session visits gets NO spoofing (pre-injection
     registers only after the first 'loaded' event). A fingerprinter reading on first paint gets the
     real locale (tr), real ultrawide resolution (3440x1440), real cores/mem, real GPU.
  B2 [HIGH] WebGL/GPU poison never effective: real "NVIDIA RTX 5070" leaks even on pass 2. Stable,
     highly-identifying hardware fingerprint.
  B3 [HIGH] HTTP Accept-Language always leaks real "tr" while JS navigator.language says de-DE ->
     cross-layer inconsistency AND real-locale disclosure. JS injection cannot rewrite HTTP headers.
     (This is the previously-known #1 de-DE gap, now proven live.)
  B4 [MEDIUM] Timezone inconsistency: Intl timezone = Europe/Berlin (July => DST => should be -120)
     but Date.getTimezoneOffset() forced to -60. Intl and Date disagree => spoof detectable.
  Plus: sec-ch-ua outs the client as "Microsoft Edge WebView2" (tiny anonymity set).

== TRACK C — MCP :8000 port/security probe (11 checks, live) ==
SECURE: C1 health(200), C2 no-token(401), C3 wrong-token(401), C9 CORS not reflected to evil origin,
        C10 SQL-injection content is parametrized (server healthy), C11 oversized source handled (no crash).
VULNERABLE (4), root-cause cluster = the authorization model:
  C5 [CRITICAL] System impersonation: any bearer-token holder sets agent_id="system" and BYPASSES all
     permission checks (profile_write succeeded). agent_id is client-supplied and self-asserted.
  C7 [CRITICAL] Privilege escalation via grant_permission: it has NO permission check. A random agent
     called grant_permission(scope="profile:write") then wrote successfully (pwn.esc). The grant PERSISTS.
  C8 [HIGH] Private-method exposure: execute_tool uses hasattr() with NO allow-list, so private/helper
     methods (e.g. _check_permission) are reachable. This is what makes grant_permission callable too.
  C6 [note] Deny-by-default is sound for a virgin agent (returns denial), but is defeated the moment C7
     is used; also the denial surfaces as an unhandled 500 in execute_tool (ingest correctly returns 403).
ROOT CAUSE: authz trusts client-supplied agent_id + exposes every attribute via hasattr + grant_permission
  is unprotected. Fixes: (1) bind agent_id to the authenticated identity (don't trust the body); (2) explicit
  allow-list of public tool names; (3) put grant_permission behind an admin-only scope; (4) catch
  PermissionError in execute_tool -> 403.
NOTE: probe ran against a TEMP vault (real vault untouched). The bearer token is stored plaintext in
  kasa.toml, so any local process that can read that file gets full access once it claims agent_id="system".

== TRACK D — Literature research (DDGS + arXiv -> local synthesis) ==
Catalog produced (MEVCUT/EKSIK). It independently flagged the same gaps we proved live: inconsistent
navigator spoofing (EKSIK), WebRTC filter evasion (EKSIK), tool-definition poisoning detector (EKSIK,
but N/A here: KASA exposes fixed tools, it does not ingest client tool-definitions), AudioContext/font
noise (EKSIK, not yet tested).
'''

def call_model(model, prompt, label, num_predict=3500, temp=0.2):
    print(f"\n[ASSESS] {label} ({model}) ...", flush=True)
    payload = json.dumps({"model": model, "prompt": prompt, "stream": True,
                          "options": {"temperature": temp, "num_predict": num_predict}}).encode()
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    buf = []
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            buf.append(obj.get("response", ""))
            if obj.get("done"):
                break
    print(f"[ASSESS] {label} bitti ({len(''.join(buf))} char)", flush=True)
    return "".join(buf)

def main():
    write_prompt = (
        "You are a senior security engineer writing a CONSOLIDATED red-team assessment for the KASA "
        "project. Use ONLY the verified findings below (all from live experiments). Do not invent. "
        "Write clear English Markdown with these sections:\n"
        "1. Executive Summary (what we tested, headline risks in 4-5 sentences).\n"
        "2. Severity Table (Finding | Track | Severity | One-line evidence | Fix). Order: CRITICAL first.\n"
        "3. Browser Identity Leaks (explain the 2-pass experiment and B1-B4 plainly).\n"
        "4. MCP Server Authorization Flaws (explain C5/C7/C8 and the shared root cause).\n"
        "5. What is already SOLID (the SECURE results + Layer-1 tests passing).\n"
        "6. Prioritized Remediation (numbered, most impactful first; tie each to a finding id).\n"
        "7. One-paragraph Turkish summary (Turkce ozet) at the very end.\n\n"
        "VERIFIED FINDINGS:\n" + FINDINGS
    )
    draft = call_model(WRITER, write_prompt, "RAPOR (taslak)")
    review_prompt = (
        "Review this KASA red-team assessment against the findings. Remove any claim not supported by "
        "the findings. Keep all 7 sections, keep severities accurate (C5/C7 and B1 are the top risks). "
        "Ensure the Turkish summary paragraph is present at the end. Output ONLY the final report.\n\n"
        "FINDINGS:\n" + FINDINGS + "\n\nDRAFT:\n" + draft[:9000]
    )
    final = call_model(REVIEWER, review_prompt, "RAPOR (inceleme)")
    out = os.path.join(HERE, "REDTEAM_ASSESSMENT.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(final.strip() + "\n")
    print(f"[ASSESS] yazildi -> {out}")

if __name__ == "__main__":
    main()
