# KASA — Özellik Ekleme Şablonu & Bilgi Dosyası

> Durum: **referans**. KASA dashboard'una yeni bir özellik/menü eklerken bu dosyadaki
> konvansiyonları ve sıfır-token orkestrasyon desenini kullan. Amaç: yerel modele (qwen)
> doğru bağlamı verip UI/UX standardına uyan, mevcut yapıyı bozmayan kod ürettirmek.
>
> İlgili kanonik dosyalar: `docs/UI_UX_STANDARD.md`, `design_system/tokens.css`.

---

## 1. Dashboard SPA yapısı (dashboard_ui/)

Dashboard tek-sayfa uygulaması (SPA); `src/dashboard/routes.py` `/dashboard`'ta sunar.

| Dosya | Rol |
|---|---|
| `dashboard_ui/index.html` | Kabuk: `<nav class="rail">` + `<section class="view">` görünümleri |
| `dashboard_ui/app.js` | Görünüm-değiştirme + veri çekme + etkileşim |
| `dashboard_ui/terms.html` | İlk açılış kullanım şartları |

### Navigasyon deseni (rail)
`<nav class="rail">` içinde her menü öğesi:
```html
<button data-view="AD" title="Başlık" aria-label="Başlık">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"
       stroke-linecap="round" stroke-linejoin="round"><!-- line-icon --></svg>
</button>
```
Mevcut görünümler: `dashboard`, `events`, `profile`, `security`, `ajan`, `audit`
(+ owner-gated `locked` butonu, `disabled`).

### Görünüm (view) deseni
Her görünüm bir bölüm:
```html
<section id="view-AD" class="view" hidden> ... </section>
```
İlk (aktif) görünümde `hidden` yoktur; nav butonunda `class="active"` bulunur.

### Görünüm-değiştirme (app.js ~satır 269-282) — JENERİK
```js
const railButtons = document.querySelectorAll('button[data-view]');
button.addEventListener('click', () => {
  const view = button.getAttribute('data-view');
  for (const section of document.querySelectorAll('.view')) { /* hide */ }
  // #view-<view> göster, tüm rail butonlarından active kaldır, tıklanana ekle
});
```
**Önemli:** Bu mantık jeneriktir — yeni bir `data-view="X"` butonu + `#view-X` bölümü
eklemek YETER; ekstra JS gerekmez, görünüm otomatik çalışır.

### Mevcut CSS sınıfları (yeniden kullan, ICAT ETME)
- Butonlar: `class="btn"`, `class="btn primary"`, `class="btn sm"`, `class="btn sm primary"`
- Görünüm kabı: `class="view"`
- Renk/spacing gerekiyorsa `design_system/tokens.css` `var(--...)` değişkenleri — hardcoded hex YOK.
- Buton olay bağlama deseni: `document.querySelector(...).addEventListener('click', async () => {...})`

---

## 2. Masaüstü katmanı (pywebview + FastAPI)

- Giriş: `kasa_app.py` → `src/desktop/launch.py:main()`
- `main()`: arka-thread'de uvicorn (127.0.0.1), ana-thread'de pywebview penceresi `/dashboard`'u gösterir.
- Veri dizini: `%APPDATA%\KASA` (`_prepare_env()`); `KASA_VAULT_PATH` / `KASA_CONFIG` env ile override edilebilir.
- Selftest kancası: `KASA_SELFTEST=<saniye>` → pencere açılıp otomatik kapanır, `SELFTEST server_ready port=...` basar.

### JS ↔ Python köprüsü (js_api)
Native yetenek (dosya diyaloğu vb.) için pywebview `js_api`:
```python
import webview
picker_api = PickerApi(...)          # window'dan ÖNCE oluştur
window = webview.create_window(..., js_api=picker_api)
picker_api.window = window           # window referansını SONRA ata
```
JS tarafı: `window.pywebview.api.<method>()` → Promise döner.

### pywebview native dosya diyaloğu (doğru API — SIK yapılan hata)
- `import webview` (top-level `create_file_dialog` importu YOKTUR).
- Sabitler: `webview.FOLDER_DIALOG`, `webview.OPEN_DIALOG`, `webview.SAVE_DIALOG`.
- Çağrı pencere üzerinden: `window.create_file_dialog(webview.FOLDER_DIALOG)`.
- Dönüş `tuple`/`list`/`None` olabilir — güvenli işle, string döndür.

---

## 3. UI/UX sabit ilkeleri (özet — tam kural: docs/UI_UX_STANDARD.md)

1. **Air-gap:** yalnız `127.0.0.1`; harici CDN/font/script/asset YOK.
2. **Read-through-redact:** UI'a giden her okuma `redact.scan()`'den geçer; ham hücre asla çıkmaz.
3. **Aggregate-first:** v1 sayı/istatistik gösterir, ham içerik değil.
4. **Tek tasarım kaynağı:** `tokens.css` + mevcut sınıflar; renk/spacing icat yok.
5. **Mühür = ölçüm:** "hardened/production-ready" ancak ampirik ölçümle.
6. **Yüksek-riskli özellikler owner-gated** (maskesiz görünüm, anahtar yönetimi) — v1'de yok.

### İş bölümü (kim yazar)
| Katman | Sahip |
|---|---|
| Sunumsal UI (HTML/CSS/JS) | yerel model (qwen) — zero-token |
| Read-through-redact güvenlik sınırı | opus/Claude elle-Edit (carve-out) |
| Orkestrasyon / splice / test | Claude (Fable) |
| Son güvenlik kontrolü | opus + deterministik gate (son söz AI'da değil) |

---

## 4. Sıfır-token orkestrasyon deseni (yerel model çağırma)

**Pipeline:** taslak → inceleme (deepseek→qwen canon), ya da odaklı tek-model.
Kod üretimi = `qwen2.5-coder:14b` (config'de "coder" rolü).

### Prompt iskeleti
```
Sen KASA projesinde kıdemli <rol>'sın. GÖREV: <net özellik>.
BAĞLAYICI KURALLAR: <UI/UX sabit ilkeleri — ilgili maddeler>.
ÜRETECEĞİN ÇIKTI: <A/B/C — dosya dosya, net>.
Mevcut kodu İNCELE ve ona GÖRE üret; imza/değişken adlarını AYNEN kullan, uydurma.
===== MEVCUT: <dosya> =====
<gerçek kod — modele SEN gömersin, model okur>
```

### Ölçülmüş parametreler (bu donanımda çalışan)
- `stream: True` (soket timeout'unu önler; hibrit prefill yavaş).
- `repeat_penalty: 1.15–1.18` — **ZORUNLU**, yoksa tekrar-döngüsü.
- `temperature: 0.15–0.4`, `top_p: 0.9`.
- `num_ctx`: girdiye göre 8192–12288. **Büyük girdi = prefill duvarı** (36KB+ tek seferde timeout).
  Çözüm: dosyayı/işi PARÇALA, ilgili slice'ları ver, tüm dosyayı değil.
- Donanım notu: 14B + orta bağlam 12GB VRAM'e sığmaz, CPU'ya taşar (~10-22 tok/s, prefill 50-100s).

### Kalite dersi
- Kod üretimi için `qwen2.5-coder:14b` güvenilir; **analiz/yargıç rolünde abliterated modeller
  güvenilmez** (yanlış-pozitif üretir). Son kontrol her zaman en güçlü model + deterministik gate.
- Yerel model çıktısı DAİMA taslaktır: splice öncesi pywebview/tokens gibi gerçek API'lere karşı
  doğrulanmalı; uygulandıktan sonra `KASA_SELFTEST` ile boot testi yapılmalı.

---

## 5. Örnek: "Ayarlar" menüsü + Dosya/Klasör Seçici ekleme (bu iş)

1. **Nav:** `<button data-view="settings">` (dişli SVG) — `audit` butonundan sonra ekle.
2. **View:** `<section id="view-settings" class="view" hidden>` — "Klasör Seç"/"Dosya Bul"
   butonları (`btn primary`/`btn`) + seçilen yol alanı. Görünüm-değiştirme otomatik çalışır.
3. **Backend:** `src/desktop/picker.py` (`PickerApi`: pick_folder/pick_file + settings.json'a kaydet).
4. **Wiring:** `launch.py` — js_api bağla (window ref sonra), `_prepare_env` kayıtlı vault_path'i oku.
5. **Test:** `KASA_SELFTEST` boot + import doğrulama. Picker tıklaması GUI → elle test.
