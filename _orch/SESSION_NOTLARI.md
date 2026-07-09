# KASA Proje — Oturum Notları
*Son güncelleme: 2026-07-02*

---

## Tamamlananlar

### MVP-0 — TAMAMLANDI ✅ (2026-07-02)
- `src/vault/schema.py` — 4 tablo DDL (events, profile, permissions, audit)
- `src/vault/database.py` — Vault sınıfı, SQLite + DPAPI
- `src/vault/audit.py` — AuditChain, SHA-256 hash zinciri
- `src/mcp_server/tools.py` — VaultTools (profile_read/write, forget, audit_read, event_ingest)
- `src/mcp_server/server.py` — FastAPI MCP sunucu, port 8000
- `src/distill/engine.py` + `scheduler.py` — qwen2.5:7b distillation, gece 02:00
- `src/tray/app.py` — PyQt5 sistem tepsisi
- `run.py` — Ana giriş noktası (argparse)
- `KURALLAR.md` — Proje yönetim kuralları (8 bölüm)
- **Entegrasyon testleri: 8/8 GEÇTİ** ✅

### V0.2 — Browser modülü (DEVAM EDİYOR 🔄)
- `browser_extension/` — Chrome Manifest V3 extension oluşturuldu (manifest.json, content.js, background.js, popup.html)
- **⚠️ Browser extension silme iptal edildi** — Klasör `d:/kasa/browser_extension/` silinmeyecek, referans olarak duracak
- **Yeni yön:** Chrome extension KALDIRILDI, yerini PyQt5/PyQt6 + QWebEngineView alıyor
  - Sebep: Chrome'a bağımlılık riski (manifest kısıtlamaları, localhost engeli, extension store)
  - QWebEngineView = Qt içine gömülü Chromium, tamamen bizim kontrolümüzde
- **Tor entegrasyonu:** V0.3 cloud masking aşamasında eklenecek (stem kütüphanesi, SOCKS5 proxy)
- Araştırma planı: Pipeline 12 — 10 sorgu hazırlandı, araştırma ajanına verilecek

---

## Güncel Mimari Karar Kaydı

| Tarih | Karar | Sebep |
|---|---|---|
| 2026-07-02 | Chrome extension → Qt WebEngine | Bağımsızlık, Chrome kısıtlama riski |
| 2026-07-02 | Browser extension klasörü silinmedi | Referans olarak saklandı |
| 2026-07-02 | Tor = V0.3, browser değil | Tor farklı tehdit modelini çözer; browser için gereksiz |
| 2026-07-02 | DPAPI + SQLite (SQLCipher değil) | Kurulum basitliği, Windows native |
| 2026-07-02 | deepseek taslak + qwen review pipeline | Sıfır token politikası — Claude orchestrate eder |

---

## Sıradaki Adım

**V0.2 — `src/browser/` modülü (Pipeline 13)**
- `BrowserWindow(QMainWindow)` — QWebEngineView tabanlı
- Sayfa yüklenince content injection → KASA MCP event_ingest
- Tray menüsüne "Tarayıcıyı Aç" eklenir

---

## Ortam Bilgisi
- Python: `C:\Users\REDACTED-USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`
- Hermes venv (uvicorn/fastapi): `C:\Users\REDACTED-USER\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`
- Ollama modeller: deepseek-coder-v2:16b-lite-instruct-q4_K_M (taslak), qwen2.5-coder:14b (review)
- VRAM: RTX 5070 12.2GB — qwen2.5-coder:14b 10.3GB, deepseek overflow RAM
- MCP sunucu: http://localhost:8000 (hermes venv ile başlatılır)
