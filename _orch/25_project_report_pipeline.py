"""
KASA Orkestrasyon — Proje Durum Raporu (yerel model uretir) v1.0
hermes3:8b rapor yazar -> qwen2.5:14b inceler/sikilastirir.
Cikti: d:/kasa/_orch/KASA_PROJECT_REPORT.md  (Claude sadece bulgulari topladi + pipeline; sifir-token)

NOT: Asagidaki FACTS blogu Claude tarafindan koddan (grep/read) cikarildi;
model YALNIZ bu gerceklere dayanarak raporu yazar (halusinasyon yok).
Prompt ve rapor INGILIZCE (kullanici istegi).
"""
import json, sys, re
import urllib.request

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA   = "http://localhost:11434/api/generate"
WRITER   = "hermes3:8b"
REVIEWER = "qwen2.5-coder:14b"

# ── Koddan cikarilan GERCEKLER (ground truth) ───────────────────────────────
FACTS = r"""
PROJECT: KASA Browser — a privacy-focused desktop browser + local memory vault.
Goal: ZERO IP / fingerprint leakage for enterprise/security use. Windows-only.
Engine: pywebview 6.2.1 -> WinForms -> WebView2 / EdgeChromium (pythonnet/clr).

== ENTRY / PROCESSES ==
- run.py (main app): init Vault (SQLite) + create schema -> start MCP server
  (FastAPI+uvicorn on 127.0.0.1:8000) in a daemon thread -> start DistillScheduler
  daemon (nightly 02:00 memory distillation) -> start PyQt5 system tray app
  (KasaTrayApp, vault LOCKED by default). Flags: --no-tray (headless), --distill-now,
  export subcommand.
- src/browser/browser_window.py (1028 lines): open_browser() creates the WebView2
  window standalone; on 'loaded' it injects JS layers. Launched directly for browsing.

== BROWSER SECURITY LAYERS (BUILT, verified in code) ==
- Layer #1 Fingerprint spoof (_PRIVACY_JS), injected pre-load via
  CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync (runs before page scripts):
    * geolocation spoof; Canvas poisoning (toDataURL/getImageData); WebGL poisoning
      (UNMASKED_RENDERER/VENDOR via getParameter); navigator spoof
      (hardwareConcurrency, deviceMemory, platform=Win32, languages/language=de-DE);
      screen=1920x1080; Date.getTimezoneOffset=-60 (Berlin/CET).
    * Privacy levels: off / standard / strict / paranoid. POISON gate = strict|paranoid.
- Layer #2 Proxy / IP hiding: config-backed (browser_config.json), applied at startup
  via env var WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--proxy-server=<addr> BEFORE the
  WebView2 env is created. Tor preset 127.0.0.1:9150. Requires restart to change.
- Layer #4 WebRTC IP-leak prevention: dual-path filter — wraps RTCPeerConnection,
  filters onicecandidate + addEventListener('icecandidate') (drops 'typ host'/'typ srflx',
  passes relay); plus a 2nd shield munging setLocalDescription SDP candidate lines.
- Sira 0 Level persistence: privacy level stored Python-side; injected as
  window.__KASA_LEVEL__ before _PRIVACY_JS so it survives cross-domain navigation.
- Recent fix (via deepseek->qwen): new windows/ads open IN THE SAME window (pywebview
  setting OPEN_EXTERNAL_LINKS_IN_BROWSER=False, was leaking to external Chrome);
  DevTools + right-click Inspect + F12 enabled (webview.start(debug=True)).
- Browser chrome present: toolbar (Back/Forward/Reload + address bar), sidebar panels
  (privacy level, Proxy/Ag). NO tabs. NO custom context menu.

== MEMORY VAULT / BACKEND (BUILT) ==
- src/mcp_server: FastAPI server on :8000. POST /v1/execute_tool runs VaultTools per
  agent_id with permission check + audit log. Serves self-hosted fonts/assets.
- VaultTools (src/mcp_server/tools.py): grant_permission, profile_read, profile_write,
  forget, audit_read, prune_expired_events, event_ingest. Each call: permission check
  (permissions table) -> op -> audit record.
- src/vault: SQLite DB; key encrypted with Windows DPAPI (no password; key bound to OS
  session) — avoids SQLCipher build pain. schema.py defines tables/indexes. audit.py.
- src/distill: engine.py uses qwen2.5:7b to distill raw interaction events into durable
  profile facts (JSON: key/value/confidence/provenance_event_ids). scheduler.py runs it
  nightly 02:00 (daemon) or on demand.
- src/export: encrypt.py exports the vault to an encrypted .kasa file (magic b"KASA",
  uint16 version, 32B salt, 12B nonce, AES-GCM). Has verify.
- src/tray: PyQt5 system tray, vault locked at start.
- Browser -> backend: an ingest JS posts browsing events to localhost:8000/v1/ingest.

== KNOWN GAPS / NOT BUILT ==
- Layer #3 Consistency engine: MISSING. navigator.languages/language and
  getTimezoneOffset are HARDCODED to de-DE / Berlin regardless of the proxy exit
  country -> inconsistency is itself a deanonymization red flag (IP=NL but lang=de-DE).
- AudioContext fingerprint noise + font enumeration defense: MISSING (only canvas/webgl
  are poisoned).
- Layer #5 Multi-site research agent bridge + research PANEL: NOT built (design stage).
  Intended: background isolated agent contexts (each through proxy+spoof+WebRTC filter),
  per-task identity isolation (anti-linkability), audit logging, results tagged
  MEVCUT/EKSIK + chunked (reuse professor-system format). Fork undecided: hybrid fetch
  (HTTP then headless) vs engine location (bridge to :8000 vs embedded runner).
- Tabs / real browser chrome: MISSING (single WebView only). Custom right-click menu:
  MISSING.
- Live verification on real fingerprint/leak sites (browserleaks) and a real proxy/Tor:
  NOT yet done.

== DEV WORKFLOW (zero-token policy) ==
- Claude ONLY orchestrates: writes pipeline scripts (_orch/NN_*.py) and splices/verifies.
- ALL feature + bugfix CODE is generated by local models: deepseek-coder-v2:16b drafts,
  qwen2.5-coder:14b reviews. Claude manually fixes only clear bugs in model output.
- Language: infra code English; comments/notes Turkish; pipeline prompts may be English.

== SCOPE BOUNDARY (explicit) ==
This tool PROTECTS its own user (privacy, anti-leak, isolation, auditable logging).
It does NOT feed sites fake data, evade bot-detection, or actively falsify fingerprints
to deceive websites. Defensive posture only.
"""

def call_model(model, prompt, label, max_tokens=2600, temp=0.2):
    print(f"\n[ORCH] {label} ({model}) cagiriliyor...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": temp, "num_predict": max_tokens}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    out = []
    with urllib.request.urlopen(req, timeout=900) as resp:
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

WRITE_PROMPT = (
    "You are a senior software architect writing a factual STATUS REPORT for the KASA "
    "project. Use ONLY the verified facts below — do not invent features, versions, or "
    "numbers. If something is a gap, say so plainly. Write in clear English, Markdown.\n\n"
    "Produce these sections, in order:\n"
    "1. Executive Summary (3-4 sentences: what KASA is, current maturity).\n"
    "2. Security Shields — BUILT (table: Shield | What it does | Status | Honest limitation).\n"
    "3. Gaps / Missing (bullet list, each with WHY it matters for a zero-leak browser; "
    "call out the hardcoded de-DE / Berlin inconsistency as the top risk).\n"
    "4. Code Structure (module -> responsibility, from the facts).\n"
    "5. Processes & Data Flow (startup sequence; browsing->ingest->nightly distill->export).\n"
    "6. Multi-site Research Agents — planned design (how they run isolated, through "
    "proxy+spoof, results tagged/chunked; the two undecided forks).\n"
    "7. Development Workflow (zero-token: local models write code, Claude orchestrates).\n"
    "8. Top 5 Next Steps (prioritized, most security-critical first).\n\n"
    "VERIFIED FACTS:\n" + FACTS
)

REVIEW_PROMPT = (
    "You are reviewing a project status report for factual accuracy and tightness. "
    "Check it against the FACTS. Remove any claim NOT supported by the facts. Keep it "
    "concise and well-structured Markdown with the same 8 sections. Ensure the hardcoded "
    "de-DE/Berlin inconsistency is flagged as the #1 gap and that the scope boundary "
    "(protects user, does not deceive sites) appears. Output ONLY the final report.\n\n"
    "FACTS:\n" + FACTS + "\n\nDRAFT REPORT:\n{DRAFT}"
)

def run():
    draft = call_model(WRITER, WRITE_PROMPT, "WRITE — project report")
    final = call_model(REVIEWER, REVIEW_PROMPT.replace("{DRAFT}", draft), "REVIEW — project report")
    with open("d:/kasa/_orch/KASA_PROJECT_REPORT.md", "w", encoding="utf-8") as f:
        f.write(final.strip() + "\n")
    print("\n[ORCH] yazildi -> d:/kasa/_orch/KASA_PROJECT_REPORT.md")

if __name__ == "__main__":
    run()
