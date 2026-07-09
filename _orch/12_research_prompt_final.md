# KASA V0.2 Browser — Araştırma Sorguları
*Tarih: 2026-07-02 | deepseek genişletti → qwen rafine etti*

## Amaç
PyQt5/PyQt6 QWebEngineView tabanlı bağımsız tarayıcı + Tor entegrasyonu +
yerel MCP sunucu güvenliği için teknik araştırma.

## Araştırma Sorguları (10 adet)
1. PyQt5 QWebEngineView JavaScript injection for page content extraction site:github.com
2. Compare PyQt6 and PyQt5 WebEngine stability in 2024-2025-2026 arxiv research
3. Tor integration with Python using stem library as SOCKS proxy for QWebEngine site:github.com
4. Security analysis of local MCP server in KASA browser (localhost attack surface) arxiv research
5. GitHub repositories similar to Project KASA (local memory + AI agent browser) site:github.com
6. Known issues and GPU performance in Qt WebEngine on Windows 11 site:github.com
7. MCP protocol implementation details in existing browser integrations site:github.com
8. Privacy-focused browsers built with Qt (comparison, architecture discussions) arxiv research
9. Tor and Qt WebEngine SOCKS5 proxy configuration guide site:github.com
10. Local-first AI agent browser architectures (research articles, blog posts 2024-2025-2026)

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
