# KASA UI/UX & Araç Standardı (v1)

> Durum: **kanonik**. Bu dosya, KASA'nın görsel/etkileşim katmanı ve bu katmanı
> üretirken kullanılacak araç/model seçimlerinin bağlayıcı kuralıdır. Gemini'nin
> `implementation_plan.md` taslağını **değerlendirir ve düzeltir** (bkz. §6).
>
> Dil kuralı: kod/altyapı İngilizce, bu belge (not/standart) Türkçe + İngilizce
> teknik terim. İlgili: `docs/PROJECT_BRIEF.md`, `docs/THREAT_MODEL.md`,
> `docs/adr/0003-at-rest-sifreleme-boslugu.md`, `design_system/tokens.css`.

---

## 1. Amaç

Kasa'yı bir veritabanı/güvenlik modülünden görünür bir ürüne çıkarırken **güvenlik
sınırını gevşetmeden** bir UI katmanı eklemek. Kural basit: *arayüz, kasanın
kalbini yeni bir saldırı yüzeyine çevirmemeli.*

## 2. Sabit İlkeler (invariants — pazarlık yok)

1. **Local-first / air-gap.** UI yalnız `127.0.0.1`'e bağlanır (config: `server.host`
   = `127.0.0.1`, `allowed_origins` = localhost). Hiçbir vault verisi dış ağa/buluta
   gitmez. Dış kaynak (CDN font, uzak script, uzak görsel) **yok** — her şey
   self-host (`/assets`) veya inline.
2. **Read-through-redact.** UI'a giden **her** okuma `src/vault/redact.py:scan()`
   kapısından geçer. Ham (deşifre edilmiş) hücre asla API'den UI'a çıkmaz. Deşifre
   → redact → JSON; sıra bu, istisnasız.
3. **Aggregate-first.** v1 panosu **sayı ve istatistik** gösterir (taranan event,
   maskelenen sır, profil anahtarı sayısı, audit zinciri durumu) — ham içerik değil.
   Event akışı gösterilecekse **maskeli** gösterilir.
4. **Yüksek-riskli iki özellik v1'de YOK.** (a) "Yetki varsa maskesiz görünüm" ve
   (b) "şifreleme anahtarı yönetimi UI" — ikisi de owner-gated ileri kademenin
   arkasında (bkz. `kasa-gelismis-kilitli-kademe`), deterministik kapı, PBKDF2,
   oturumluk. v1 salt-okunurdur, hiçbir sır ifşa etmez, anahtara dokunmaz.
5. **Tek tasarım kaynağı.** `design_system/tokens.css` kanonik. `browser_window.py`
   → `_DESIGN_CSS` ona **senkron** kalır (önce token'da değişir, sonra taşınır).
   Yeni yüzeyler bu token'ları kullanır; renk/spacing icat etmez.
6. **Mühür = ölçüm.** "enterprise-grade / hardened / production-ready" etiketi
   **ampirik ölçülene** kadar kullanılmaz — ne kodda, ne UI'da, ne pazarlamada.
   Özellikle: at-rest tam-DB şifreleme HENÜZ mühürlü değil (ADR 0003), dolayısıyla
   UI "diskte şifreli" iddiasını **kapalı** tutar; yalnız app-layer cell AES-GCM'in
   kapsadığını söyler.

## 3. Teknoloji Kararı — Ne KULLANIRIZ / Ne KULLANMAYIZ

### Kullan (mevcut olanı sömür, yeniden yazma)
- **Backend/API:** var olan **FastAPI** (`src/mcp_server/server.py`, `127.0.0.1:8000`,
  bearer + CORS + authz allow-list). Panonun salt-okunur uçları buraya eklenir;
  paralel ikinci API kurulmaz.
- **Render yüzeyi:** var olan **WebView2** (`src/browser/browser_window.py`) veya
  herhangi bir yerel tarayıcı. Pano = FastAPI'nin localhost'tan sunduğu **static SPA**
  (vanilla/hafif JS) — native build yok.
- **Tasarım dili:** `design_system/tokens.css` + inline SVG line-icon'lar (zaten var).

### Kullanma (ve neden)
- **Tauri / Electron → HAYIR.** Bu makinede C/Rust/Node build-toolchain **yok** —
  SQLCipher'ı çıkmaza sokan duvarın aynısı (ADR 0003 fizibilite dersi). WebView2 +
  FastAPI zaten yerel render veriyor; ikinci runtime = boşuna kırılganlık.
- **ComfyUI / raster AI-görsel üretimi → HAYIR.** Bir güvenlik panosu tipografik ve
  veri-yoğun olmalı, illüstrasyon-yoğun değil. AI-üretimi raster görsel: (a) marka
  tutarlılığını bozar, (b) air-gap'i kirletir (harici model/asset), (c) "ciddi, güven
  veren" tona ters, (d) SVG line-icon + token zaten mevcut. Kazanç sıfır, maliyet gerçek.
- **Bulut subagent (Claude) → HAYIR.** zero-token politikası: sunumsal UI kodu yerel
  modellerin işi. Bulut token'ı yalnız orkestrasyon (Fable-5) ve güvenlik sınırı (opus)
  için harcanır.

### Anthropic-ailesi araçlarından UI/UX'e UYAN tek şey
- **Artifact (claude.ai önizleme) → EVET, ama yalnız `sahte veri` ile.** UI/UX
  görseldir; anlatmak yerine göstermek için hızlı, paylaşılabilir prototip yüzeyi.
  Kural: artifact'e **asla** gerçek vault verisi girmez (air-gap). Onaylanan tasarım
  yerel static SPA'ya port edilir. Gerçek pano her zaman **yalnız yereldir**.

## 4. İş Bölümü (kim ne yazar)

| Katman | Sahip | Neden |
|---|---|---|
| Sunumsal UI (HTML/CSS/JS, bileşen) | yerel model (deepseek→qwen) | zero-token; jenerik feature kodu |
| Read-through-redact güvenlik sınırı (stats aggregator, uçlar) | **opus (elle-Edit)** | güvenlik-kritik carve-out; sızıntı = tüm tezi bozar |
| Orkestrasyon / entegrasyon / QC gate | Fable-5 şef | üç-kademe mimari (ADR 0001) |
| Son güvenlik kontrolü (false-PASS avı) | opus + deterministik gate | son söz asla AI'da değil (deterministik) |

## 5. Bilgi Mimarisi (v1 navigasyon)

1. **Dashboard** — sistem durumu: taranan event sayısı, maskelenen sır sayısı,
   profil anahtarı sayısı, audit zinciri bütünlüğü, at-rest kapsama durumu (dürüst).
2. **Events** — son olaylar, **maskeli** (redact.scan çıktısı). Ham gösterim yok.
3. **Profile** — kalıcı bilgiler, maskeli okuma.
4. **Security Center** — v1: entropi/prefix kuralları ve benchmark sonuçlarının
   **salt-okunur** özeti. Anahtar yönetimi ve maskesiz görünüm owner-gated (v2+).

## 6. Gemini `implementation_plan.md` Değerlendirmesi (rapor protokolü)

Genel: yön doğru ve air-gap konusunda övgüye değer bilinçli. Düzeltmeler:
- **(a) Var olanı yeniden öneriyor.** "Local API/BFF eklenecek" ve "Design System"
  → ikisi de **var** (FastAPI + tokens.css). Karar: üstüne inşa et, yeniden kurma.
- **(b) Temeli abartıyor.** "cell_crypt = Data at Rest ✓" → tam-DB at-rest **mühürlü
  değil** (ADR 0003; SQLCipher toolchain'siz, app-layer cell AES-GCM kısmi). UI bunu
  "bitti" diye sunmaz.
- **(c) Tauri/Electron = toolchain tuzağı** (§3). Static SPA + WebView2 ile değiştirildi.
- **(d) İki yüksek-riskli özellik** (maskesiz görünüm, anahtar yönetimi) **v1'den
  çıkarıldı**, owner-gated'e ertelendi (§2.4).
- **PDF render:** kozmetik, düşük öncelik; en sona, istenirse.

## 7. Doğrulama (bu standarda uyum testi)

- **İzolasyon testi:** pano ayaktayken hiçbir istek `127.0.0.1` dışına gitmemeli
  (ağ izleme). Dış origin CORS'ta reddedilmeli.
- **Read-through-redact testi:** pano uçlarının döndürdüğü hiçbir JSON'da ham sır
  bulunmamalı; deşifre edilmiş ham hücre response'a **hiç** girmemeli (aggregate +
  redact.scan çıktısı dışında veri yok).
- **Token tutarlılığı:** yeni UI yalnız `tokens.css` değişkenlerini kullanmalı;
  hardcoded renk = red.
