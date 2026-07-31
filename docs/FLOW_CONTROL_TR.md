# KASA Debi-Kontrol Katmanı (DEBI-0..3) — Sebep → Karar → Sonuç

Tarih: 2026-07-31 · Durum: uygulandı, 13 yeni test, tam paket 189 geçti / 1 xfail (önceden mevcut)

KASA'nın savunma mimarisi (şifreleme, yetkilendirme, enjeksiyon bariyerleri) zaten
güçlüydü; zayıf tarafı **kaynak yönetimiydi**: ajanların yazma hızını, audit zincirinin
büyümesini ve aynı olayın kaç kez saklandığını sınırlayan hiçbir şey yoktu. Bu katman
dört deterministik vana ekler. Hiçbiri modele güvenmez — "model güvenlik sınırı
değildir" değişmezi (KURALLAR §4) ile tutarlıdır.

---

## DEBI-0 — Ajan başına hız sınırı

- **Sebep:** Halüsinasyon döngüsüne giren bir ajan `event_ingest` / `profile_write`
  çağrılarını sınırsız atabilirdi. Her çağrı hem kasaya yazar hem audit zincirine kayıt
  ekler; tek delirmiş ajan diski doldurup zinciri şişirebilirdi (yerel DoS). Hiçbir
  katman geri-basınç uygulamıyordu.
- **Karar:** Token-bucket sınırlayıcı (`src/mcp_server/ratelimit.py`, varsayılan patlama
  60, dolum 1 token/sn), ağ sınırında `/v1/execute_tool` ve `/v1/ingest` içinde ve izin
  kontrolünden **önce** uygulanır — çünkü reddedilen çağrı bile iş yapar (audit kaydı
  yazar). Kovalar `agent_id` başınadır.
- **Sonuç:** Kapasite üstü çağrılar HTTP 429 ile döner; ne DB'ye ne zincire dokunur.
  Delirmiş tek ajan diğerlerini aç bırakamaz (izole kovalar); kasanın toplam yazma
  debisi artık kesin bir tavana sahiptir.

## DEBI-1 — Olay alımında tekilleştirme (anahtarlı özet + sayaç)

- **Sebep:** Tekrarlayan olaylar ("kullanıcı maili açtı", günlük sayfa ziyaretleri) her
  seferinde yeni satır olarak yazılıyordu. Tekrar hem diski şişiriyordu hem de — daha
  kötüsü — maliyeti O(satır) olan `forget()` decrypt-taramasını büyütüyordu. Asıl değerli
  sinyal olan *tekrar sayısı* (rutin) ise hiç yakalanmıyordu.
- **Karar:** Alım anında `content_hash = HMAC-SHA256(kasa_anahtarı, source|type|içerik)`
  hesaplanır (redact SONRASI, şifreleme ÖNCESİ). Eşleşme varsa yeni satır açılmaz:
  `occurrence_count` artar, `last_seen` güncellenir, `ttl_expiry` uzar ve `distilled=0`
  sıfırlanır — yükselen frekans damıtmaya taze sinyal olarak geri döner. **Anahtarlı**
  özet bilinçli tercihtir: düz SHA-256, düşük entropili içerikte DB dosyasından sözlük
  saldırısına izin verirdi; HMAC anahtarı DPAPI korumalıdır, DB dosyası tek başına
  eşitlik bilgisi sızdırmaz.
- **Sonuç:** "Aynı olay 365 kez" = 1 satır + sayaç. Depolama ve `forget()` tarama
  maliyeti tekrar ile büyümez; sayacın kendisi, kullanıcının sistemden istediği
  davranış/rutin analizi girdisine dönüşür ("N tekrar = alışkanlık") — ham log değil,
  davranış.

## DEBI-2 — Audit zinciri checkpoint & arşiv

- **Sebep:** Audit zinciri tasarımı gereği yalnızca uca ekler (T7: kurcalama tespit
  edilir); satır silmek `verify_chain`'i kırmadan mümkün değildi. Bu garantinin bedeli
  vardı: çıkışı olmayan sınırsız büyüme — çıkmaz sokak.
- **Karar:** Yeni `audit_checkpoint` tablosu zinciri o anki ucunda mühürler
  (`upto_id`, `upto_hash`). `archive_up_to(checkpoint)` **yalnızca mühürlenmiş**
  satırları silebilir. `verify_chain` genesis yerine mühür hash'inden tohumlanır — ve
  tohum lafla değil *tabloyla doğrulanır*: `previous_hash`'i hiçbir kayıtlı mühürle
  eşleşmeyen ilk satır doğrulamayı düşürür (testli). `_get_last_hash`, tablo boşsa son
  mühre düşer; tam arşiv sonrası zincir süreklidir. Araçlar (`audit_checkpoint` /
  `audit_archive`, kapsam `admin:audit`) bilerek `PUBLIC_TOOLS` dışıdır: arşivleme
  sahibin/bakımın işidir, ağdan asla çağrılamaz.
- **Sonuç:** Eski audit aralıkları bütünlük bozulmadan arşivlenebilir; arşiv sonrası
  kurcalama yine tespit edilir. Mühürsüz kayıt asla silinemez.
- **Yan bulgu (düzeltildi):** `rotate_db_key` zinciri sabit genesis tohumundan yeniden
  kuruyor ve mühürleri bayat hash'lerde bırakıyordu; *checkpoint → rotate → arşiv*
  sırası doğrulamayı kırardı. Rotasyon artık kalan ilk satırın tohumunu korur ve canlı
  mühürleri yeniden hesaplanan hash'lere taşır.

## DEBI-3 — Prune'da köken-koruyan mezar taşı (tombstone)

- **Sebep:** `prune_expired_events` süresi dolan satırları tamamen siliyordu; oysa
  `profile.provenance` event-ID saklar. Referanslı bir satırın silinmesi, "bu profil
  bilgisi nereden türedi" zincirini sessizce koparıyordu — KASA'nın başka her yerde inşa
  ettiği denetlenebilirliğin tam tersi.
- **Karar:** Prune sırasında herhangi bir profil girdisinin referansladığı satırlar
  silinmez; `content` alanı `tombstone:<content_hash>` işaretiyle değiştirilir (diskten
  gerçek silme — `secure_delete=ON`). Referanssız satırlar eskisi gibi tamamen silinir.
  Mezar taşları dedup eşleşmesine girmez (tekrarlayan olay taze satır açar) ve sonraki
  prune'larda yeniden sayılmaz (idempotent). `forget()` bilinçli olarak **muaftır**:
  unutulma hakkı (T5) köken zincirinden üstündür, orada gerçek silme sürer.
- **Sonuç:** Hassas içerik zamanında diskten gider, köken zinciri çözülebilir kalır.
  GDPR-tipi silme değişmemiştir.

---

## Doğrulama

`tests/test_flow_control.py` (13 test): dedup tek-satır/sayaç, source-type ayrımı,
distilled sıfırlama; taşmada 429, ajan-başı kova izolasyonu; arşiv zinciri korur, arşiv
sonrası kurcalama yakalanır, mühürsüz silme reddedilir, sahte tohum reddedilir;
tombstone/silme ayrımı, prune idempotenliği, tombstone dedup-dışı, `forget` gerçek
silmeye devam eder. Tam paket: **189 geçti, 1 xfail** (önceden mevcut) — regresyon yok.

## Uyumluluk

Şema değişiklikleri `Vault.connect()` içinde idempotent `ALTER TABLE` migration'larıdır;
mevcut kasalar yerinde yükselir. `event_ingest` yanıtına `deduplicated` alanı,
`prune_expired_events` yanıtına `deleted` yanında `tombstoned` alanı eklendi.
