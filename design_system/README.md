# KASA Design System v0.1 — Yerel Bileşen Kütüphanesi

Bu klasör, KASA'nın görsel dilinin **tek kaynağıdır** (single source of truth).
Amaç: tarayıcı arayüzü, landing sayfası ve gelecekteki tüm UI aynı token ve
bileşenleri miras alsın — tutarlılık koda değil, buraya bağlı olsun.

## İçerik
| Dosya | Ne |
|-------|-----|
| `tokens.css` | Kanonik CSS değişkenleri (renk, gölge, hareket, yarıçap, font) + `@font-face`. **Değişiklik önce burada.** |
| `index.html` | Görsel showcase — renkler, tipografi, yükseklik, hareket, bileşenler, rail+panel mock. Tarayıcıda aç: `design_system/index.html`. |

## Kullanım
Herhangi bir sayfa/görsel için:
```html
<link rel="stylesheet" href="/path/to/design_system/tokens.css">
```
Sonra token'ları `var(--kasa-...)` ile kullan (asla ham hex gömme):
```css
.buton { background: var(--kasa-primary); border-radius: var(--kasa-r-sm); }
```

## Tutarlılık kuralı (önemli)
Şu an tarayıcı (`src/browser/browser_window.py` → `_DESIGN_CSS`) aynı değerleri
**satır-içi** taşıyor. Bu kütüphane o değerlerden **birebir** çıkarıldı. İki kaynak
elle senkron tutulur:
1. Bir token değişecekse **önce `tokens.css`**'te değişir.
2. Sonra `_DESIGN_CSS` bloğuna yansıtılır.
3. (İleride refaktör: `_DESIGN_CSS` bu dosyayı doğrudan okuyup tek kaynağa insin —
   o zaman senkron kendiliğinden olur.)

## Bulut senkron (opsiyonel, ertelendi)
Bu kütüphane **DesignSync / `/design-sync`** ile claude.ai/design'daki bir Design
System projesine senkron edilmeye hazırdır (görsel panelde bileşen kartları,
sürüm takibi). Bilinçli karar: KASA yerel-öncelik olduğundan şimdilik **buluta
itilmedi**; istenirse her bileşen için preview HTML'e `<!-- @dsCard group="..." -->`
işaretçisi eklenip sync edilir.
