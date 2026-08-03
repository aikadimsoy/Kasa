# Değişiklik Günlüğü / Changelog

Bu dosya KASA'nın kayda değer değişikliklerini tutar.
Biçim [Keep a Changelog](https://keepachangelog.com/) yaklaşımına dayanır.

> **Sürüm kuralı (KURALLAR T2):** sürüm numarasını AI *önerir*, **sahip ilan eder**.
> Aşağıdaki `0.1.0` MVP-0 için önerilen ilk kamuya açık sürümdür.

---

## [0.1.0] — 2026-08-03 — ilk kamuya açık sürüm

MVP-0 çekirdeği: yerel-öncelikli şifreli hafıza kasası + izin-aracılı MCP sunucusu.

### Eklendi
- **Vault çekirdeği** — SQLite şeması (`events`, `profile`, `permissions`, `audit`),
  hücre-başı AES-GCM şifreleme (AAD ile bağlama bağlı), Windows DPAPI ile korunan anahtar.
- **MCP sunucusu** — yalnız loopback (127.0.0.1), bearer kimlik doğrulama,
  `PUBLIC_TOOLS` allow-list, ajan-başı token-bucket hız sınırlama.
- **İzin modeli** — deny-by-default kapsam hesabı; kararı **deterministik kod** verir,
  model değil (`src/mcp_server/`, `src/agent/gate.py`).
- **Denetim kaydı** — hash-zincirli (her kayıt bir öncekinin SHA-256'sını taşır),
  tahrif tespiti doğrulanabilir.
- **Damıtma** — yerel model (Ollama) ile ham olaylardan profil çıkarımı; köken (provenance)
  zorunluluğu ve deterministik QC kapısı.
- **Ajan köprüsü** — sınırlı araç-çağrısı döngüsü, salt-okunur maskeli dashboard yüzeyi.
- **MCP adaptörü** — MCP istemcilerini (Claude Code vb.) çalışan sunucuya bağlar;
  ayrıcalıklı yol tutmaz, her çağrı mevcut kapılardan geçer.
- **Masaüstü** — sistem tepsisi uygulaması, kurulum ön-kontrolü, kullanım şartları onayı.
- **Ölçüm tezgahları** — `tools/security_bench/` (güvenlik damgası),
  `tools/model_bench/` (model karşılaştırma damgası).
- **Red-team araçları** — `_orch/redteam/` altında izole sunucuya karşı canlı saldırı,
  kalıcı saldırgan, kanıt toplama ve named-pipe süreç-kimliği fizibilite ölçümü.
- **Belgeler** — proje şartnamesi, tehdit modeli, ADR'ler, ölçüm damgaları,
  eğitim/öğretim çerçeve programı.

### Güvenlik
- `audit_read` ve `prune_expired_events` için **yetkisiz deneme artık denetim izine yazılır**
  (önceden sessiz kalıyordu — adli iz boşluğu).
- Hız sınırlayıcı sözlüğüne **üst sınır + LRU tahliye** eklendi; istemci-beyanlı `agent_id`
  ile sınırsız bellek büyümesi kapatıldı.
- Yeni üretilen bearer token artık **DPAPI ile korunarak** saklanır (düz metin yerine).
- **KASA tarayıcısı varsayılan olarak KAPALI.** `open_browser()`, `KASA_ENABLE_BROWSER=1`
  ayarlanmadıkça başlamaz ve **hiçbir yan etki oluşmadan önce** reddeder (proxy ortamı
  uygulanmaz, pencere açılmaz, `js_api` köprüsü kurulmaz). Sebep: köprü ziyaret edilen
  sayfanın JS bağlamında bulunuyor ve sayfa betikleri origin denetimi olmadan enjekte
  ediliyor → ziyaret edilen her site `set_proxy()` / `ingest()` çağırabiliyor. Ayrıntı ve
  dürüst sınırlar: `SECURITY.md`, "Known-unsafe surfaces".
- **Adres çubuğunda çift-çözümleme açığı kapatıldı.** Sayfa URL'si HTML dizgesine
  gömülürken yalnız `"` kaçırılıyor, `&` kaçırılmıyordu; URL artık DOM `.value` özelliğiyle
  atanıyor, böylece kaçırma sorusu tümüyle ortadan kalkıyor.
- Yukarıdaki ikisi `tests/test_browser_optin_gate.py` ile mühürlendi — **negatif kontrol**
  (eski açık kalıbı 3/3 yakalanıyor) ve **pozitif kontrol** (opt-in verilince akış kapının
  ötesine geçiyor, yani kapı "her zaman reddet" değil) birlikte.

### Bilinen sınırlar (dürüst beyan)
- `agent_id` **istemci-beyanlıdır**: token sahibi başka bir ayrıcalıklı kimliği taklit
  edebilir (F-IMP). v1 tehdit modeli "yerel süreç güvenilir" varsayar; bkz. `SECURITY.md`.
- `kasa.db` **tam** at-rest şifreli değildir; yalnız üç sütun şifrelidir (bkz. `docs/adr/0003`).
- Ağ çıkışı (egress) henüz **ölçülmemiştir**; ilgili plan `docs/GUVENLIK_CIKIS_PLANI.md`.
- Prompt injection sektör genelinde açık bir problemdir; KASA'nın savunması **yapısaldır**
  (model asla güvenlik sınırı değildir), dokunulmazlık iddiası değildir.
- **Tarayıcı köprü izolasyonu açıktır** (yukarıda). Kapı, yüzeyi varsayılan olarak
  kapatır — kusuru **düzeltmez**. Düzgün çözüm mimaridir: pywebview'da `js_api` pencere
  başınadır, origin başına değil; sayfa bağlamına konan hiçbir şey (nonce dâhil) sayfadan
  gizlenemez. Ayrıcalıklı arayüzü sayfa bağlamının dışına almak yol haritasındadır.
  Bulgu kod yapısından kuruldu; **çalışan bir sömürü yazılmadı ve koşulmadı** — bu satır
  ölçüldüğü seviyede duruyor, bir üstünde değil.
- Bu sürüm bir **araştırma önizlemesidir**; üretim veya hassas veri için önerilmez. Projenin
  kendi güvenlik tezgâhı `docs/SECURITY_BENCHMARK.md` kararı **yayına hazır değil**'dir ve
  bu bilinerek yayımlanmaktadır.

### Lisans
- Kaynak kod **AGPL-3.0-or-later** ile yayımlanır (`LICENSE`).
- Ticari/kapalı-kaynak kullanım için ikinci yol: `COMMERCIAL.md` (dual-lisans).
