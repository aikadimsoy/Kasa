# -*- coding: utf-8 -*-
"""
KASA Red-Team — Guvenlik Acigi LITERATUR arastirmasi (sifir-token) v1.0
DDGS + arXiv -> hermes3:8b sentez -> qwen2.5-coder:14b inceleme.
Cikti:
  redteam/RESEARCH_FINDINGS.md   (insan-okur katalog, [MEVCUT]/[EKSIK] etiketli)
  redteam/attack_catalog.json    (makine-okur: uygulanacak testler)

Amac: KASA'nin tehdit yuzeyi (MCP sunucu + tarayici parmak-izi) icin literaturden
somut, test-edilebilir saldiri/kontrol fikirleri cikar. Professor formati: her madde
[MEVCUT] (mevcut test planinda var) veya [EKSIK] (bosluk -> yeni test) diye etiketli.

Calistir: venv312 python (DDGS + requests var).
"""
import json, sys, os, time, re, urllib.request, urllib.parse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

OLLAMA   = "http://localhost:11434/api/generate"
WRITER   = "hermes3:8b"
REVIEWER = "qwen2.5-coder:14b"
HERE     = os.path.dirname(os.path.abspath(__file__))

# Arastirma sorgulari — KASA tehdit modeline gore
QUERIES = [
    "MCP Model Context Protocol server security tool poisoning vulnerability",
    "MCP tool description prompt injection rug pull cross-server shadowing attack",
    "FastAPI bearer token auth bypass CORS misconfiguration security",
    "browser fingerprinting deanonymization canvas webgl audio font entropy",
    "navigator spoofing inconsistency detection fingerprint anti-detect browser",
    "WebRTC IP leak timezone language mismatch fingerprint deanonymization",
    "SQLite injection audit log tampering hash chain integrity attack",
]

def ddg_search(query, k=5):
    """DDGS ile arama; basarisizsa bos liste."""
    try:
        from duckduckgo_search import DDGS
        out = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=k):
                out.append({"title": r.get("title", ""),
                            "body": r.get("body", ""),
                            "href": r.get("href", "")})
        return out
    except Exception as e:
        print(f"[RESEARCH] DDG hata ({query[:40]}...): {e}", flush=True)
        return []

def arxiv_search(query, k=3):
    """arXiv API — guvenlik makaleleri."""
    try:
        url = ("http://export.arxiv.org/api/query?search_query="
               + urllib.parse.quote(query)
               + f"&start=0&max_results={k}")
        with urllib.request.urlopen(url, timeout=30) as r:
            xml = r.read().decode(errors="replace")
        titles = re.findall(r"<title>(.*?)</title>", xml, re.DOTALL)[1:]  # ilk baslik feed basligi
        summaries = re.findall(r"<summary>(.*?)</summary>", xml, re.DOTALL)
        out = []
        for t, s in zip(titles, summaries):
            out.append({"title": t.strip().replace("\n", " "),
                        "body": s.strip().replace("\n", " ")[:600], "href": "arxiv"})
        return out
    except Exception as e:
        print(f"[RESEARCH] arXiv hata: {e}", flush=True)
        return []

def call_model(model, prompt, label, num_predict=3500, temp=0.2):
    print(f"\n[RESEARCH] {label} ({model}) ...", flush=True)
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
    print(f"[RESEARCH] {label} bitti ({len(''.join(buf))} char)", flush=True)
    return "".join(buf)

def main():
    corpus = []
    for q in QUERIES:
        print(f"[RESEARCH] Sorgu: {q}", flush=True)
        hits = ddg_search(q, 5) + arxiv_search(q, 2)
        for h in hits:
            corpus.append(f"- ({q[:30]}) {h['title']}: {h['body'][:300]}")
        time.sleep(2)  # DDG rate-limit nezaketi
    corpus_txt = "\n".join(corpus)[:12000]
    with open(os.path.join(HERE, "research_corpus.txt"), "w", encoding="utf-8") as f:
        f.write(corpus_txt)
    print(f"[RESEARCH] Corpus toplandi: {len(corpus)} kayit", flush=True)

    # KASA'nin mevcut savunmalari (etiketleme icin baglam)
    kasa_ctx = (
        "KASA CURRENT DEFENSES (label [MEVCUT] if literature threat is already addressed/tested, "
        "else [EKSIK]):\n"
        "- MCP :8000 requires Bearer token (secrets.compare_digest); CORS allow_origins = localhost only.\n"
        "- Tools deny-by-default via permissions table; agent_id='system' bypasses.\n"
        "- Audit is SHA-256 hash-chained (tamper-evident); verify_chain().\n"
        "- Browser Layer#1 spoofs canvas/webgl/navigator/screen/timezone to HARDCODED de-DE/Berlin.\n"
        "- WebRTC dual-path filter drops host/srflx candidates. Proxy via WebView2 arg.\n"
        "- KNOWN GAP: hardcoded de-DE regardless of proxy exit country -> inconsistency = deanon flag.\n"
        "- NOT built: tool-definition poisoning detector, AudioContext/font noise, Layer#3 consistency engine.\n"
    )

    write_prompt = (
        "You are a security researcher. From the LITERATURE SNIPPETS below, extract concrete, "
        "TESTABLE attack/check ideas relevant to KASA (a local MCP memory-vault server on :8000 + "
        "an anti-fingerprint WebView2 browser). For EACH idea output a bullet:\n"
        "  [MEVCUT] or [EKSIK] | Category | Attack name | one-line how-to-test\n"
        "Tag [MEVCUT] if KASA already defends/tests it, [EKSIK] if it's a gap. Be specific and "
        "practical (things a local script can actually try against :8000 or the browser). "
        "Group by category: MCP-API, Tool-Poisoning, Fingerprint, Network-Leak, Vault-Integrity.\n\n"
        + kasa_ctx + "\n\nLITERATURE SNIPPETS:\n" + corpus_txt
    )
    draft = call_model(WRITER, write_prompt, "SENTEZ (taslak)")
    with open(os.path.join(HERE, "research_draft.md"), "w", encoding="utf-8") as f:
        f.write(draft)

    review_prompt = (
        "Review and tighten this KASA security-test catalog against the KASA defenses. Ensure every "
        "line is TESTABLE and correctly tagged [MEVCUT]/[EKSIK]. Remove vague/duplicate lines. Keep "
        "the 5 categories. Then, AFTER the catalog, append a fenced ```json block: a list of objects "
        '{\"id\":str,\"category\":str,\"name\":str,\"tag\":\"MEVCUT|EKSIK\",\"how_to_test\":str,'
        '\"target\":\"mcp|browser\"} for the [EKSIK] items only (the new attacks to actually run). '
        "Output the markdown catalog then the json block.\n\n"
        + kasa_ctx + "\n\nDRAFT CATALOG:\n" + draft[:9000]
    )
    final = call_model(REVIEWER, review_prompt, "SENTEZ (inceleme)")

    with open(os.path.join(HERE, "RESEARCH_FINDINGS.md"), "w", encoding="utf-8") as f:
        f.write(final.strip() + "\n")
    # JSON blogu ayikla
    m = re.search(r"```json\s*\r?\n(.*?)```", final, re.DOTALL)
    if m:
        try:
            catalog = json.loads(m.group(1))
            with open(os.path.join(HERE, "attack_catalog.json"), "w", encoding="utf-8") as f:
                json.dump(catalog, f, ensure_ascii=False, indent=2)
            print(f"[RESEARCH] attack_catalog.json: {len(catalog)} EKSIK saldiri", flush=True)
        except Exception as e:
            print(f"[RESEARCH] JSON ayikla hata: {e}", flush=True)
    print("[RESEARCH] TAMAM -> RESEARCH_FINDINGS.md", flush=True)

if __name__ == "__main__":
    main()
