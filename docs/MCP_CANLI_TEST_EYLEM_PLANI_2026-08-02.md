# KASA MCP Canlı Saldırı Testi — Bulgular ve Sıralı Eylem Planı
**Tarih:** 2026-08-02
**Araç:** `_orch/redteam/live_mcp_attack.py` (izole sunucu; gerçek vault'a dokunmaz)
**Kayıt:** `_orch/redteam/live_attack_log.jsonl`

---

## 1. Ne ürettik

İzole bir KASA MCP sunucusuna karşı **25 sıralı saldırı + 2 saldırı-sonrası bütünlük
kontrolü** koşan canlı bir test aracı. Dört saldırı yüzeyini + zincir bütünlüğünü yokluyor:

| Aile | Kapsam | Sonuç |
|---|---|---|
| A1–A7 | Kimlik doğrulama, rezerve kimlik, bilinmeyen araç, hız-sınırı, içerik | 6 DİRENDİ + A6 açık |
| B1–B7 | **İzin modeli / deny-by-default** (okuma/yazma/forget/audit/prune/grant/kapsam) | 7/7 DİRENDİ |
| D1–D5 | Girdi robustluğu (boyut/aralık/tip/bilinmeyen-eksik param) + iç-detay sızıntısı | 5/5 DİRENDİ, sızıntı yok |
| F1–F2 | CORS cross-origin + HTTP method karışıklığı | 2/2 DİRENDİ |
| G1–G2 | Batch amplifikasyonu + batch atomikliği | G1 DİRENDİ, G2 açık |
| H1 | Rezerve kimlik varyantları (isim baypası) | DİRENDİ (yetki kazanmıyor) |
| E1 | Sınırsız kova (bellek DoS) | açık |
| C1–C2 | Audit zinciri sağlam mı + ret adli iz bıraktı mı | C1 SAĞLAM, C2 gap |

**Özet: 22 savunma testi → 22'si tuttu. Audit zinciri fırtına sonrası sağlam. 1 gözlem
(sessiz ret). Ayrıca: 1 post-auth kimlik zayıflığı (A6), 1 sertleştirme kalemi (E1),
1 atomiklik nüansı (G2) — bunlar EŞİT AĞIRLIKTA "açık" değildir (bkz. §2.5).**

### Ölçüm dürüstlüğü notu
C1 ilk koşuda "ZİNCİR BOZUK" dedi; bu **yanlıştı** — bütünlük aleti sunucu thread'indeki
SQLite bağlantısına ana thread'den erişip thread hatası aldı ve bunu "zincir bozuk" diye
gösterdi (sahte-kırmızı). Alet düzeltildi (ana thread'de taze salt-okuyan bağlantı) →
zincir gerçekten sağlam çıktı. **"Aletin mi yoksa kasanın mı yanlış olduğu" ayrılmadan
bulgu ilan edilmedi.** Ayrıca H1 homoglif testi cp1254 konsolda basılırken çökmüştü;
aracın kendi çıktısı UTF-8'e sabitlendi (bu oturumun "UTF-8'i pinle" dersi araca uygulandı).

---

## 2. Bulgular (kök neden + kanıt + düzeltme + doğrulama)

### F-A6 — Hız-sınırı baypası (dönen agent_id)
- **Kök neden:** `agent_id` istemci-beyanlı; token-bucket kovası `agent_id`'ye göre tutuluyor
  ([ratelimit.py:26](../src/mcp_server/ratelimit.py#L26)). Her istekte kimlik değişince kova hiç dolmaz.
- **Kanıt (canlı):** dönen kimlikle 120/120 istek geçti, hiç 429 yok. Sabit kimlikle 62. istekte 429.
- **Düzeltme:** P1 kimlik bağlama (aşağıda) — token↔agent_id bağlanır, kimlik rastgele iddia edilemez.
- **Alet doğrulaması:** A6 tekrar koş → "ACIK" satırı "savunma gelmiş"e dönmeli.

### F-IMP — Ayrıcalıklı kimlik taklidi (`browser`) · *ısrarcı saldırgan senaryosunda keşfedildi*
- **Araç:** `_orch/redteam/persistent_attacker.py` (kendi günlüğü: `attacker_journal.jsonl`).
- **Kök neden:** `agent_id` istemci-beyanlı ve `RESERVED_AGENT_IDS` yalnız `{"system"}`.
  `browser` rezerve DEĞİL ama `events:write` iznine sahip (startup auto-grant). Token'ı olan
  bir saldırgan `agent_id="browser"` diyerek bu izni **devralır**.
- **Kanıt (canlı):** izole sunucuda `browser` gibi `event_ingest` → **HTTP 200** (yazma başarılı).
  Diğer tüm hedefler (profil oku, forget, audit oku) ısrarlı denemeye rağmen 403/404 ile tuttu.
- **Şiddet:** A6'dan **daha ağır**. A6 yalnız hız-sınırını aşıyor (DoS); F-IMP ayrıcalıklı bir
  ajan olarak **yazma** veriyor → olay-deposu zehirleme / damıtmaya dolaylı enjeksiyon yüzeyi.
  Yine post-auth (token gerekir) ama bütünlük etkisi gerçek.
- **Düzeltme:** **P1 kimlik bağlama** (aynı kök). Token→agent_id çözülür; gövdedeki agent_id
  token'ın sahibiyle eşleşmezse reddedilir. Böylece "browser" taklidi kapanır.
- **Nüans (dürüst):** yetki delindi AMA audit breach'i **kaydetti** (`event_ingest` başarı satırı).
  Yani authz başarısız, gözlemlenebilirlik başarılı — adli iz var. (audit_read reddi ise sessiz;
  bkz. C2-GAP.)
- **Bu bulgu P1'i Adım 2'den daha yukarı çekmeli** — sıralama gözden geçirilecek.

### F-E1 — Sınırsız kova (bellek DoS) · *bu testte keşfedildi*
- **Kök neden:** `RateLimiter._buckets` sözlüğünün **tahliyesi yok** ([ratelimit.py:23](../src/mcp_server/ratelimit.py#L23)).
  Dönen kimlik freni baypas etmekle kalmaz, her yeni kimlik **kalıcı bir kova** açar.
- **Kanıt (canlı):** 3000 dönen kimlik → 3000 kova, `delta=3000` (doğrusal, sınırsız).
- **Düzeltme:** kovaya tahliye ekle — dolu-kova için son-görülme zaman-aşımıyla temizlik
  (kova zaten `capacity`'ye dolmuşsa saklamaya gerek yok) ya da toplam kova sayısına LRU sınırı.
- **Alet doğrulaması:** E1 tekrar koş → `delta` artık ~n olmamalı; kova sayısı üst-sınırlı kalmalı.

### F-G2 — Batch işlemsel değil (kısmi yürütme) · *bu testte keşfedildi*
- **Kök neden:** `execute_tool` döngüsü her `tool_call`'u tek tek çalıştırıp commit ediyor;
  sonraki bir çağrı 404/hata verirse önceki commit **geri alınmıyor** ([server.py:158-193](../src/mcp_server/server.py#L158-L193)).
- **Kanıt (canlı):** [gecerli event_ingest, bilinmeyen araç] batch'i 404 döndü ama ilk olay
  yazıldı (`events_before=1 → events_after=2`).
- **Düzeltme (KARAR gerektirir):** ya tüm batch tek transaction (hepsi-ya-hiç), ya da
  davranış bilerek belgelenir (her yazma izin-kapılı + audit'li olduğundan kısmi yürütme
  kabul edilebilir). Bkz. Karar 2.
- **Alet doğrulaması:** G2 tekrar koş → transaction seçilirse `partial_write=false` olmalı.

### F-C2GAP — Sessiz ret (audit_read + prune) · *bu testte keşfedildi*
- **Kök neden:** `audit_read` ([tools.py:236](../src/mcp_server/tools.py#L236)) ve
  `prune_expired_events` ([tools.py:293](../src/mcp_server/tools.py#L293)) izin reddinde,
  diğer araçların aksine, `audit_chain.record(..., "permission_denied")` **çağırmıyor**.
- **Kanıt (canlı):** C2'de kayıtlı ret türleri `{profile_read, forget, profile_write}` —
  `audit_read`/`prune` yok. Yetkisiz denetim/temizlik denemesi **görünmez**.
- **Düzeltme:** iki metoda da, raise'den önce, diğerleriyle aynı `permission_denied` audit satırı.
- **Alet doğrulaması:** araç tekrar koş → C2 GAP listesi boşalmalı.

---

## 2.5 Dürüst şiddet çerçevesi ve ölçülen kontroller (2026-08-02 sonradan eklendi)

Önceki "3 açık" ifadesi fazla-iddialıydı. Düzeltme, nedenleriyle:

- **Tehdit modeli:** A1/A2 dışındaki TÜM testler geçerli bearer token'la koştu. Yani bunlar
  "uzaktan kırılım" değil, **ele geçirilmiş/kötü niyetli yerel ajan** senaryolarıdır.
  Perimetre (token + rezerve-id + namespace) tuttu.
- **A6** = gerçek, ama kök neden "hız-sınırı bozuk" değil, **kimlik doğrulanmıyor** (P1'in semptomu).
- **E1** = sertleştirme kalemi: yavaş doğrusal sızıntı (GB için milyonlarca istek), anlık çökme değil.
- **G2** = güvenlik açığı DEĞİL, işlemsel atomiklik nüansı. Kısmi yazma, ajanın zaten
  yapabileceği yetkili bir yazmadır; yeni yetenek vermez.

**Ölçülen kontroller** (teoriyi doğrulamak için sonradan koşuldu):

| Kontrol | Ölçüm | Sonuç |
|---|---|---|
| **Pozitif (deny ayrımı)** | Yetkili `goodagent` → profile_read; yetkisiz `attacker` → profile_read | **200 vs 403** — sistem gerçekten AYIRIYOR, blanket-deny değil |
| **Negatif (tamper tespiti)** | `verify_chain` tamper öncesi/sonrası | **True → False** — naif tamper YAKALANDI |

**İki dürüst sınır:**
- **C1:** `verify_chain` naif tamper'ı yakalar (ölçüldü). Tüm zinciri ileri yeniden hesaplayan
  saldırganı yakalamak **checkpoint / dış-kopya çapasına** bağlıdır — bu test EDİLMEDİ.
  Hash zinciri tamper-**evident**'tir, tamper-**proof** değil.
- **A7:** yalnızca "içerik saklanır, çalıştırılmaz"ı test eder (depolama zaten çalıştırmaz).
  Asıl enjeksiyon riski (içeriğin geri okunup **modele** verilmesi) ajan döngüsündedir; bu
  araç onu yoklamaz. A7 "DİRENDİ" zayıf bir kanıttır.

## 2.6 UYGULANANLAR (2026-08-02, "A kovası" + v2 spike)

Ölçüm gösterdi: token `kasa.toml`'da **düz metin** ([config.py](../src/config.py)), taşıma
**loopback HTTP**, ve [dashboard/routes.py:12-13](../src/dashboard/routes.py#L12-L13) **v1 tehdit
modelini** ("yerel süreç zaten güvenilir") açıkça belgelemiş. Yani F-IMP/A6 v1'de kapsam dışı;
asıl karar v1 mi v2 mi. Her iki modelde doğru olan "A kovası" + v2 fizibilite spike'ı yapıldı:

| İş | Durum | Kanıt |
|---|---|---|
| **C2-GAP** (audit_read/prune reddi kaydı) | ✅ kapandı | canlı araç özeti artık "sessiz ret (GAP)" basmıyor |
| **E1** (kova tahliyesi, `max_buckets`) | ✅ kapandı | [tests/test_ratelimit_eviction.py](../tests/test_ratelimit_eviction.py) — 2000 kimlik → ≤100 kova |
| **Token DPAPI** (yeni token korumalı) | ✅ eklendi | `get_or_create_bearer_token` DPAPI'ye yazar; legacy düz metin dokunulmadan okunur |
| **v2 spike** (named-pipe süreç kimliği) | ✅ fizibıl | [named_pipe_identity_spike.py](../_orch/redteam/named_pipe_identity_spike.py) — kernel PID'i sırsız verdi |
| Regresyon | ✅ yok | `214 passed, 1 xfailed` |

**Kalan asıl karar (senin):** v1'de mi kalınacak, v2'ye (OS süreç kimliği) mi geçilecek.
Spike v2'nin Windows'ta çalıştığını kanıtladı; token şemaları (rotation/rolling) v2 yerine
DEĞİL, v2 gerekirse onun üstüne. F-IMP/A6 yalnız v2 kararıyla kapanır.

## 3. Sıralı eylem planı

**İlke:** ucuz + yerel + düşük-risk + aletle doğrulanabilir olan önce. Her adımın sonunda
`live_mcp_attack.py` tekrar koşulur; alet bir **kabul kapısı** görevi görür (kırmızı→yeşil
kanıtı, tahminle değil canlı ölçümle).

### Adım 1 — Küçük yerel düzeltmeler (aynı gün, düşük risk)
Tek dosya, birkaç satır, mevcut testleri kırmaz; aletle anında doğrulanır.

- **1a · C2-GAP (sessiz ret).** `audit_read` ve `prune` reddine `permission_denied` audit
  satırı ekle. Efor: ~2 satır × 2 yer. Doğrulama: C2 GAP kalkar. Ek: bunu koruyan bir
  birim test (`tests/test_denial_is_audited.py`).
- **1b · E1 (sınırsız kova).** `RateLimiter`'a tahliye: dolu-kova zaman-aşımı temizliği veya
  kova sayısı LRU sınırı. Efor: ~15 satır + test. Doğrulama: E1 `delta` üst-sınırlı.
  Mevcut `test_ratelimit*` (varsa) yeşil kalmalı.

### Adım 2 — P1 kimlik bağlama (A6'nın kök çözümü; mimari)
- Per-agent token; `verify_token` token'dan `agent_id` çözer; istek gövdesindeki `agent_id`
  ile eşleşmezse **reddet**. Böylece dönen agent_id token'a bağlanır → A6 kapanır ve
  tüm authz yüzeyi güçlenir.
- **Karar 1 gerekir** (aşağıda): token↔agent_id eşlemesi nerede tutulacak + geriye uyumluluk.
- Efor: orta (kendi tasarım notu + testleri). Doğrulama: A6 "ACIK" → "savunma gelmiş".

### Adım 3 — G2 batch atomikliği (karar sonrası)
- **Karar 2**'ye göre: transaction sarma **veya** bilinçli belgeleme. Efor: transaction
  seçilirse ~10 satır (döngüyü tek commit'e sar, hata → rollback). Doğrulama: G2.

### Adım 4 — Repo hijyeni + secret triyajı (güvenlikten bağımsız, paralel yürüyebilir)
- **4a · Git (ONAY gerekir).** `build_nuitka*/` → `.gitignore` + `git rm --cached -r`
  (diskten **SİLMEZ**, yalnız staging'den çıkarır). 1.479 dosya staging'i temizler.
- **4b · 16 secret triyajı.** Her biri kaldır ya da gerekçeyle `secret_allowlist.json`
  (kasa.toml:4 bearer bilinen; test fixture'ları muhtemel yanlış-pozitif).

---

## 4. Kararlar (senin — peşinen verilmedi)

**Karar 1 — P1 token↔agent_id eşlemesi nerede?**
- (a) `kasa.toml`'da statik harita (basit, az ajan) ·
- (b) DB `permissions`/yeni tablo (dinamik, döndürülebilir) ·
- (c) `.vaultkey` yanında ayrı korumalı dosya.
Öneri: mevcut tek-token modeliyle geriye uyumlu kalacak (b), ama az ajanlık MVP için (a) yeter.

**Karar 2 — Batch atomikliği?**
- (a) Tek transaction (hepsi-ya-hiç) — daha güvenli, biraz kod ·
- (b) Kısmi yürütmeyi belgele — her yazma zaten izin-kapılı + audit'li olduğundan kabul edilebilir.
Öneri: (a); "kasadaki yazma ya tamamen olur ya hiç olmaz" ilkesi denetlenebilirlikle tutarlı.

---

## 5. Doğrulama disiplini
Her adımdan sonra: `py -3.14 _orch/redteam/live_mcp_attack.py` + `py -3.14 -m pytest tests/
-q --ignore=tests/browser`. İddia yok, ölçüm var: kırmızı→yeşil canlı gösterilir.
