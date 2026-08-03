# KASA Profil Eğitimi — 15 Günlük Plan + Devir (Fable-şef)

> 2026-07-10 · Fable-5 (şef) hazırladı · Kullanıcı 15 gün yok · Kanonik devir belgesi.
> İlkeler: **makine sağlığı** (kontrollü, yormadan) · **dürüstlük** (sahte grinding yok) ·
> **sıfır-token** (yerel modeller çalışır) · **air-gap** · son söz deterministik gate'te.

## Dürüst gerçek (önce bunu oku)
Kaynak veri **statiktir** (sen yoksun → yeni gezinme olayı gelmez). 77 olay birkaç turda
**doyuma ulaşır**; aynı veriyi 15 gün öğütmek yeni bilgi üretmez, sadece makineyi yorar.
Bu yüzden Fable-şef kararı: **asıl eğitim Gün 1'de yapıldı** (kontrollü çok-model konsensüs),
kalan günler için **yeni veri gelirse çalışan nazik bir gözcü** bırakıldı (yoksa boşta).

## Gün 1 (bugün) — YAPILDI ✅
Kontrollü çok-model konsensüs kampanyası (`_orch/training/enrich_campaign.py`):
- Modeller **sırayla** (hermes3:8b → qwen2.5:7b), aralarında soğuma; sonra küçük modellerle
  (qwen2.5:3b, llama3.2:3b) doyum kontrolü → **0 yeni** (doyum onaylandı).
- **Fable checklist** (`_orch/training/fable_checklist.md`) + deterministik gate (namespace
  allow-list + credential deny + provenance-gerçek-olaylardan) her adayı eledi.
- **Profil 3 → 6 fact** (DB yedeği + audit + supersedes; rollback mümkün):
  - `user.habits.privacy_testing` (güncellendi, 2-model konsensüs, 46 provenance)
  - `user.habits.web_security` (yeni — canvas fingerprint kontrolü)
  - `user.preferences.<REDAKTE-A>` (mevcut)
  - `user.preferences.<REDAKTE-B>` (yeni — 2 provenance)
  - `user.preferences.privacy.search` (yeni — güven 1.0, 24 provenance)
  - `user.name` (mevcut)
- `user.profile.*` (kimlik) **boş kaldı** — gezinme olayları istikrarlı kimlik vermez.
  Bu dürüst sonuç; uydurma kimlik yazmadım (halüsinasyon = vault kirliliği).

## Gün 2–15 — Nazik delta-gözcü (opsiyonel; senin bir komutunla açılır)
`_orch/training/watch_delta.py` (test edildi: seed=77, sonra boşta):
- Günde 1x çalışır. **Yeni olay ≥ 5** ise: DB yedeği alır → kampanyayı delta'da çalıştırır
  (checklist+gate, günlük tavan 6, sabit 15 dk timeout) → profili günceller.
- Yeni veri yoksa: `IDLE` yazar ve çıkar (**sıfıra-yakın yük**, makine yorulmaz).
- Fable yokken "şef kalitesi" = checklist+gate deterministik uygulanır (son söz kuralda).

### Otonom çalışmasını istersen (senin kararın — ben sessizce kurmadım)
Zamanlanmış görev kurulumu **persistence** olduğu için otomatik-mod reddetti (doğru davranış:
makinene habersiz kalıcı görev koymam). İstersen **sen** tek satırla kur:
```
schtasks /Create /TN "KASA_Training_Watch" /TR "d:\kasa\_orch\training\run_watch.cmd" /SC DAILY /ST 05:00 /F
```
Kaldırmak için:
```
schtasks /Delete /TN "KASA_Training_Watch" /F
```
Kurmasan da sorun yok: veri statik olduğu için gözcü zaten çoğunlukla boşta olurdu. Dönünce
elle de çalıştırabilirsin: `py d:\kasa\_orch\training\watch_delta.py`.

## Makine sağlığı (senin direktifin)
- Sıralı çıkarım (paralel ağır yük YOK) + modeller arası soğuma.
- Küçük/orta modeller tercih; günlük tavan; sabit timeout; Ollama kapalıysa nazik çıkış.
- Gözcü günde 1x + yalnız yeni-veri varsa çalışır → %99 boşta. Makineyi uyandırmaz.

## Dönünce ne yap (inceleme + geri alma)
- **Profili gör:** KASA.exe → Profil sekmesi (maskeli), veya
  `py -c "import sqlite3;print([r[0] for r in sqlite3.connect('d:/kasa/kasa.db').execute('SELECT key FROM profile')])"`
- **Ne yazıldı:** `_orch/training/logs/campaign_*.log` + `candidates_*.json` (her adayın gerekçesi).
- **Gözcü günlüğü:** `_orch/training/logs/watch.log`.
- **Geri al (rollback):** eğitim öncesi yedek `d:/kasa/_bak_archive/kasa_pretrain_*.db`.
  Geri yükleme: KASA kapalıyken `copy _bak_archive\kasa_pretrain_<ts>.db kasa.db`.
- **Audit bütünlüğü:** her yazım audit zincirine + supersedes'e işlendi (Güvenlik sekmesi doğrular).

## Ayrıca bu oturumda tamamlanan (build)
- `KASA.exe` (25.6 MB, onefile, kaynak-korumalı) — Ajan paneli + Yarış Modu + **yeni tasarım**
  (KASA tokens.css: sohbet balonları, model çipleri, iz satırları; markdown temizliği).
