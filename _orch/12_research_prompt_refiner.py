"""
Pipeline 12 — Araştırma promptunu yerel modellere düzenlettir
deepseek genişletir → qwen netleştirir → 12_research_prompt_final.md'ye yazar
"""
import json, re, os
import urllib.request

OLLAMA   = "http://localhost:11434/api/generate"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"
ORCH     = "d:/kasa/_orch"

def call_model(model, prompt, label):
    print(f"\n[ORCH] {label} ({model})...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": 0.3, "num_predict": 4000}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
                                  headers={"Content-Type": "application/json"})
    buf = []
    with urllib.request.urlopen(req, timeout=300) as r:
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

DRAFT_PROMPT = """
You are a research prompt engineer. Your job is to expand and refine a research brief into
exactly 10 precise, distinct research queries that a web research agent can execute independently.

## Project Context
Project KASA is a local-first, encrypted memory vault for Windows (SQLite + DPAPI).
It exposes memory to AI agents via MCP (Model Context Protocol) server on localhost:8000.

## What we are planning to build next
A standalone embedded browser using **PyQt5/PyQt6 + QWebEngineView** (Qt's embedded Chromium)
that replaces the Chrome extension approach. The browser will:
- Read page content (URL, title, body text) and send to KASA vault via localhost MCP
- Optionally route traffic through **Tor** (for V0.3 cloud masking)
- Be fully under user control — no Chrome, no Google, no extension store dependency

## Draft research topics (expand these into 10 precise queries):
1. PyQt5 QWebEngineView page content extraction (JavaScript injection, DOM reading)
2. PyQt6 vs PyQt5 WebEngine — which is more stable in 2025-2026
3. Tor integration with Python browser (stem library, SOCKS proxy, QWebEngine proxy settings)
4. Security risks: local MCP server + embedded browser (CSRF, localhost attack surface)
5. Similar projects on GitHub (local browser + local AI memory)
6. Qt WebEngine known issues on Windows 11 (GPU, sandbox, permissions)
7. MCP protocol + browser integration — existing implementations
8. Privacy browsers built with Qt (existing art, architecture decisions)
9. Tor + Qt WebEngine SOCKS5 proxy configuration
10. Local-first AI agent browser architectures (research papers, blog posts 2024-2026)

## Your task
Rewrite these 10 topics as 10 PRECISE search queries. Each query should:
- Be specific enough for a web search agent to find exact results
- Cover GitHub repos, academic papers, blog posts, Stack Overflow, documentation
- Include relevant keywords (library names, versions, error messages, concepts)
- Be in ENGLISH
- Be numbered 1-10

Output format — plain numbered list, no headers, no explanations:
1. <query>
2. <query>
...
10. <query>
""".strip()

raw1 = call_model(DRAFTER, DRAFT_PROMPT, "PROMPT GENISLETME")
with open(f"{ORCH}/12_draft_queries.txt", "w", encoding="utf-8") as f:
    f.write(raw1)

REFINE_PROMPT = f"""
You are a research quality reviewer. Below are 10 research queries drafted for a web research agent.
Review them and improve each one to be maximally useful for finding:
- GitHub repositories (add "site:github.com" where relevant)
- Academic/technical papers (add "arxiv" or "research" where relevant)
- Recent articles (add "2024 OR 2025 OR 2026" where relevant)
- Technical documentation and bug reports

## Project: PyQt5/PyQt6 QWebEngineView embedded browser + Tor + local MCP server (KASA vault)

## Draft queries:
{raw1[:3000]}

## Rules for refinement:
- Keep exactly 10 queries
- Make each query more specific with exact library names, version numbers, search operators
- Add one query about "technological compatibility risks" and one about "known solutions to common problems"
- Output ONLY the numbered list 1-10, nothing else

Output:
1. <refined query>
...
10. <refined query>
""".strip()

raw2 = call_model(REVIEWER, REFINE_PROMPT, "PROMPT RAFINE")
with open(f"{ORCH}/12_refined_queries.txt", "w", encoding="utf-8") as f:
    f.write(raw2)

# Son promptu markdown dosyasına yaz
queries = raw2.strip()
final_md = f"""# KASA V0.2 Browser — Araştırma Sorguları
*Tarih: 2026-07-02 | deepseek genişletti → qwen rafine etti*

## Amaç
PyQt5/PyQt6 QWebEngineView tabanlı bağımsız tarayıcı + Tor entegrasyonu +
yerel MCP sunucu güvenliği için teknik araştırma.

## Araştırma Sorguları (10 adet)
{queries}

## Araştırılacak Kaynaklar
- GitHub repoları
- Teknik makaleler ve bloglar (2024-2026)
- Stack Overflow / Qt forums
- arXiv / research papers
- Bilinen sorunlar ve çözümleri

## Not
Browser extension silme iptal edildi — chrome extension `d:/kasa/browser_extension/`
klasöründe durmaya devam eder (geçici referans). Ana geliştirme PyQt embedded
browser modülüne (`d:/kasa/src/browser/`) taşınıyor.
"""

with open(f"{ORCH}/12_research_prompt_final.md", "w", encoding="utf-8") as f:
    f.write(final_md)

print(f"\n[ORCH] Arastirma promptu hazir: {ORCH}/12_research_prompt_final.md")
print("[ORCH] Pipeline 12 tamamlandi.")
