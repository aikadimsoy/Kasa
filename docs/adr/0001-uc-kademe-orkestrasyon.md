# ADR-0001 — Üç-Kademe Zero-Token Orkestrasyon

## Durum
Kabul edildi

## Bağlam
- KASA'nın zero-token politikası var: yerel modeller kodu yazar, koda bulut token harcanmaz.
- Yerel modelleri güvenilir şekilde organize etmek gerekiyor.
- Yerel modeller öz-incelemede zayıf; kanıt: üretilen benchmark kodunda yaklaşık 8 kusur bulundu, birçoğu sessiz false-PASS (yanlış GEÇTI) üretebilecek nitelikteydi.

## Karar
- Üç kademe tanımlandı:
  (1) Yerel işçiler deepseek -> qwen: KODU YAZAR.
  (2) Fable-5 şefi: ORGANİZE eder (spec yazar, iş dağıtır, ilk geçiş inceleme yapar) ama kod yazmaz.
  (3) opus + deterministik test-gate: güvenlik son-kontrolörü.
- Zero-token kuralı KODA aittir; şef bulut token harcar. Doğru ifade: 'kod zero-token, orkestrasyon düşük-token'.

## Sonuçlar
- Opus token maliyeti düşer.
- Kod yerel kalır.
- En güçlü model (opus) son güvenlik otoritesi olarak kalır.
- Şef tek-nokta-arıza değildir; kontrolör (opus) backstop görevi görür.
- Guardrail şart: şef kod yazmaz, belirsizlikte eskale eder.
