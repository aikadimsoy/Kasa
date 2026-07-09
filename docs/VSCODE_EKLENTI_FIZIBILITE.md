# KASA VS Code Eklentisi — Fizibilite & Mimari Plan

**Belge türü:** Fizibilite + mimari + aşamalı plan (kod ÖNCESİ karar belgesi)
**Durum:** 🟡 TASLAK — inşa kararı bekliyor. Onaysız kod yazılmaz.
**Soru:** "Bu tarayıcıya bağlı bir VS Code uygulaması yapılabilir mi?"

---

## 0. Karar (özet)
**Evet, yapılabilir — ve mimarinin zaten öngördüğü şey.** KASA'nın tezi: vault, izin-aracılı
MCP üzerinden *herhangi bir yetkili ajana* açılır (brief §1/§4). VS Code eklentisi = yetkili bir
MCP istemcisi. Brief ilk müşteri olarak "sahibin Claude'u + KisiselAsistan"ı sayar; eklenti bunun
dogfooding kanıtı olur. **Ama iki gerçek sınır var (§3) ve PlanAgent ile örtüşme kararı (§4).**

---

## 1. Doğrulanmış bağlantı yüzeyi (keşif sonucu)
`src/mcp_server/server.py`:
- **Auth:** tek `Bearer` token — `get_or_create_bearer_token(cfg)` config'ten okunur/üretilir;
  `verify_token` `secrets.compare_digest` ile denetler. Eklenti aynı makinede olduğundan token'ı
  KASA config'inden okur.
- **Kimlik:** her istek gövdesinde `agent_id`. `RESERVED_AGENT_IDS={"system"}` reddedilir (C5).
  Eklenti kendi kimliğiyle gelir: `agent_id="vscode"`.
- **Endpoint'ler:**
  - `POST /v1/execute_tool` → `profile_read(scope)`, `profile_write`, `forget`, `audit_read(range)`,
    `event_ingest`, `prune_expired_events` — hepsi broker'da scope-denetimli.
  - `POST /v1/ingest` → olay yükleme.
  - `GET /` → sağlık.
- **İzinler:** `permissions(agent_id, scope, granted_at)` tablosu. Lifespan'de "browser" ajanına
  `events:write` OTOMATİK veriliyor — aynı desenle "vscode" ajanına gereken scope'lar
  (`profile:read:all`, `events:read`, `admin:forget` ...) verilir.
- **Config köprüsü:** `browser_config.json` (`agent_model`, `privacy_level`, `adv_pw`) — eklenti
  bunu okuyup yazabilir → model/gizlilik/kilit VS Code'dan yönetilir.

## 2. Ne yapabilir (rol paleti)
| Rol | Kanal | Değer |
|-----|-------|-------|
| İzleme/bekçi | audit JSONL izleme + `audit_read` polling | canlı "ne oldu" görünürlüğü |
| Kontrol | `browser_config.json` R/W + `run.py` başlat/durdur | model/gizlilik/kilit VS Code'dan |
| Vault gezgini | `execute_tool: profile_read/write/forget` | kasayı VS Code'da aç/düzenle |
| Dev köprüsü | süreç + log + `pytest` | başlat/durdur/test/log |

## 3. İki dürüst sınır (kritik)
1. **Canlı-push kanalı YOK.** MCP sunucusu istek/yanıt; SSE/WebSocket yok. `event_bus.py`
   **KASA'da değil, PlanAgent'ta** (in-process). Yani gerçek-zamanlı izleme için üç seçenek:
   - **(A) Audit JSONL dosyasını izle** — append-only hash-chain log; VS Code `FileSystemWatcher`
     yeni satırları canlı render eder. **Sunucu değişikliği YOK.** ← önerilen (en temiz, thin-edge).
   - (B) `audit_read`/events polling (örn. 2 sn) — basit ama gecikmeli/gürültülü.
   - (C) MCP'ye küçük bir `GET /v1/events/stream` (SSE) ekle — en canlı ama sunucuya dokunur
     (test-then-fix, authz kapsamı genişler).
2. **Native tarayıcı penceresini VS Code'a GÖMEMEZSİN.** KASA browser bir WebView2/OS penceresi;
   eklenti ona *bağlanır/yansıtır*, chrome'unu barındırmaz. Sayfaları VS Code webview'inde açmak
   *ayrı* bir üründür ve WebView2 gizlilik katmanını kaybeder → kapsam dışı.

## 4. PlanAgent örtüşmesi (karar gerektirir)
`D:\PlanAgent` zaten PyQt ile: `dashboard_window`, `loop_window`, `models_page`, `activity_panel`,
`core/event_bus`, `core/permission_broker`, `kpi_report`, `telemetry`. Yani **izleme/kontrol hub'ı
zaten var.** Üç yol:
- **(a) Taşı:** izleme rolünü VS Code'a taşı ("VS Code dock" tercihinle uyumlu — [[planagent-ui-tercihleri]]),
  PlanAgent'ı emekliye ayır/incelt. Büyük ama tutarlı.
- **(b) Rol ayır:** PlanAgent ekosistem-geneli kalsın; VS Code eklentisi yalnız **KASA'ya özel**
  (vault gezgini + kontrol). Örtüşme az.
- **(c) Köprüle:** PlanAgent'ın `event_bus`'ını bir yerel sokete/dosyaya köprüle, eklenti onu okusun.

## 5. Mimari (inşa edilirse)
```
kasa-vscode/  (TypeScript, VS Code Extension API)
  package.json         # contributes: viewsContainer (activity bar), commands, config
  src/
    extension.ts       # activate(): panelleri + komutları kaydet
    kasaClient.ts      # MCP istemcisi: fetch :8000, Bearer + agent_id="vscode"
    config.ts          # KASA config + browser_config.json R/W (model/level/lock)
    auditWatcher.ts    # audit JSONL FileSystemWatcher -> olay akışı (§3-A)
    views/
      monitorView.ts   # webview/tree: ingest'ler, audit, güvenlik durumu
      controlView.ts   # model seç, gizlilik, Gelişmiş kilit, başlat/durdur
      vaultView.ts     # profile_read/write/forget
```
- **Yeniden kullanım:** `design_system/tokens.css` webview'lerde import edilir → aynı görsel dil.
- **Invariant uyumu:** eklenti "ince kenar" (zekâ yok); `agent_id="vscode"` broker'dan geçer;
  deny-by-default; token yalnız yerel okunur, loglanmaz. Değişmez 1-2 korunur.

## 6. Aşamalı plan
- **F0 — İskele + bağlantı kanıtı:** extension iskeleti, `kasaClient` `GET /` + `audit_read`;
  "vscode" ajanına scope grant (lifespan'e ekle veya tek-sefer komut). Çıktı: VS Code'da
  bir komut audit'i çekiyor.
- **F1 — İzleme paneli (§3-A):** audit JSONL watcher → activity-bar webview'inde canlı akış +
  güvenlik durumu (privacy_level, adv kilit). `tokens.css` ile stillenir.
- **F2 — Kontrol paneli:** `browser_config.json` R/W (model/level), `run.py` başlat/durdur.
- **F3 — Vault gezgini:** `profile_read/write/forget`.
- **F4 (opsiyonel):** canlı-push için SSE endpoint (§3-C) veya PlanAgent devri (§4-a).

## 7. Risk & maliyet
| Konu | Değerlendirme |
|------|----------------|
| Teknik fizibilite | Yüksek — hazır HTTP+token API, dosya-izleme; VS Code API standart |
| En büyük belirsizlik | PlanAgent örtüşme kararı (§4) — netleşmeden F1+ dağınık olur |
| Güvenlik | Token'ı eklentide düz tutma; yalnız config'ten oku, output'a yazma. Scope minimal. |
| Efor | F0-F1 makul (birkaç oturum); F4/PlanAgent devri büyük |
| Sıfır-token | Eklenti kodu greenfield TS → yerel modeller mi, elle mi? (VS Code/TS, yerel coder modellerinin zayıf alanı olabilir — karar gerekir) |

## 8. Karar bekleyen sorular (senin)
1. **Rol** (§2): önce İzleme mi, Kontrol mü, Vault mü?
2. **PlanAgent** (§4): taşı / rol-ayır / köprüle?
3. **Canlı-olay** (§3): audit-dosya izleme (A, önerilen) / polling (B) / SSE ekle (C)?
4. **Sıfır-token:** TS eklenti kodunu yerel modeller mi üretsin, yoksa bu VS Code/TS işi
   elle-yazım carve-out'u mu (browser_window.py gibi)?

---
*Hazırlayan: Claude, fizibilite önerisi. Tüm uçlar `server.py`/config'ten doğrulandı; canlı-push
ve gömme sınırları dürüstçe işaretlendi. İnşa, bu belge + §8 kararları onaylanınca başlar.*
