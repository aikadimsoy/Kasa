# KASA — Bağımsız Denetim ve Projeksiyon

_Ölçüm tarihi: 2026-08-01 · commit `2dfda9e` · Yöntem: salt-okunur inceleme + testlerin ve
güvenlik tezgahının fiilen koşturulması + izole ortamda saldırı denemesi._

_Bu belge iddia değil ölçüm raporudur. Ölçülmeyen her satır "ölçülmedi" diye işaretlidir._

---

## 0. Önce düzeltme — kendi önceki cevabımı geri alıyorum

Daha önce sana at-rest hakkında şunu söyledim: *"benchmark kasa.db'ye bir canary yazıyor,
ham dosyada buldu, 8096. byte'ta. Yani kasa.db düz metin bir SQLite dosyası"* ve
*"sqlcipher3 import edilemeyince kod sessizce normal sqlite3'e düşüyor."*

**İkisi de yanlıştı.** Ölçüm:

| İddiam | Gerçek | Kanıt |
|---|---|---|
| Canary ham dosyada bulundu → içerik düz metin | `CRYPTO-ATREST` **PASS** | bugünkü koşu: "canary absent from kasa.db + yan dosyalar" |
| SQLCipher sessizce sqlite3'e düşüyor | Böyle bir fallback **kodda yok** | [database.py:183-189](../src/vault/database.py#L183) — sqlcipher import girişimi hiç yok |
| At-rest kapatılmamış bir açık | **Bilinçli, belgelenmiş karar** | [THREAT_MODEL.md §L2](THREAT_MODEL.md) — gerekçesi, sınırı, tripwire'ı yazılı |

Aradaki fark önemsiz değil: "sessiz hata" ile "belgelenmiş takas" farklı şeyler ve farklı
şey yapmayı gerektirirler. Sessiz hata düzeltilir; belgelenmiş takas ya kabul edilir ya
yeniden açılır — ama panikle değil, tripwire koşulu gerçekleşince.

**Gerçekten doğru olan tek kısım:** `kasa.db` şifreli bir dosya *değil*, düz SQLite. Ama
bu, içeriğin okunabildiği anlamına gelmiyor. Aşağıda tam tablo var.

---

## 1. At-rest gerçekte ne durumda (kolon kolon ölçüm)

Canlı vault üzerinde (`d:\kasa\kasa.db`, 794.624 bayt, 175 adet `K1:` şifreli hücre):

| Tablo | Kolon | Durum | Örneklem |
|---|---|---|---|
| events | **content** | **ŞİFRELİ** | 77/77 |
| events | timestamp, session_id, source, type, ttl_expiry, distilled | düz metin | 77/77 |
| profile | **value** | **ŞİFRELİ** | 6/6 |
| profile | key, provenance, created_at, updated_at | düz metin | 6/6 |
| audit | **details** | **ŞİFRELİ** | 92/92 |
| audit | timestamp, agent_id, action, previous_hash, entry_hash | düz metin | 92/92 |
| permissions | tümü | düz metin | 1/1 |

Dosya başlığı `SQLite format 3` — yani dosya açılabiliyor, ama **içerik kolonları
açılmıyor**. AES-256-GCM, hücre başına rastgele nonce, AAD ile bağlamına bağlı.

### Peki düz metin metadata ne açık ediyor?

Şifreli kolonlara **hiç dokunmadan**, sadece düz kolonlardan çıkardığım profil:

```
user.habits.privacy_testing          (46 olaydan türemiş)
user.habits.web_security             (5 olaydan)
user.preferences.<REDAKTE-A>         (9 olaydan)
user.preferences.privacy.search      (24 olaydan)
user.preferences.<REDAKTE-B>         (9 olaydan)
user.name

browser/page_visit  74 olay · test_script/manual 3 olay
2 oturum · 2026-07-02 04:00 → 23:02
audit: browser 74 event_ingest, system 8 profile_write, 1 forget
```

> **[REDAKSİYON — 2026-08-03, public yayın öncesi]** İki profil fact'inin **alan adı**
> maskelendi (`<REDAKTE-A>`, `<REDAKTE-B>`): sahibin gerçek kişisel tercih alanını açığa
> vuruyorlardı. **Olay sayıları, oturum penceresi ve mekanizma değişmedi** — bulgunun kanıt
> değeri aynen duruyor: düz metin metadata, şifreli kolonlara hiç dokunmadan profil çıkarmaya
> yetiyor. Orijinal değerler sahibin yerel arşivinde (`_private_archive/`, yayınlanmaz).

Yani dosyayı ele geçiren biri **tercihin ayrıntısını (hangi marka/sağlayıcı) öğrenemez**, ama
*"bu kişi gizlilik testi ve web güvenliğiyle ilgileniyor, şu kategorilerde yerleşik tercihleri
var, 2 Temmuz'da sabah 4'ten gece 11'e kadar 74 sayfa gezmiş"* bilgisini eksiksiz alır.

**Sebep:** bu kolonlar sorgulanabilir olmak zorunda (indeks, TTL taraması, hash zinciri).
Şifrelenirlerse `WHERE ttl_expiry < ?` ve audit zinciri çalışmaz.
**Sonuç:** içerik gizli, **desen açık**. Gizlilik literatüründe bilinen ayrım: metadata
çoğu zaman içerikten daha çok şey söyler. THREAT_MODEL bunu rezidüel olarak *listelemiş* —
yani gizlenmiyor — ama "düşük hassasiyet" değerlendirmesi bence fazla iyimser.

---

## 2. Bugünün ölçüm tablosu

| Ölçüm | Sonuç |
|---|---|
| Test paketi (`--ignore=tests/browser`) | **189 passed, 1 xfailed** |
| Tam paket (sağlık raporu, bugün 04:35) | 192 passed, 1 xfailed |
| Güvenlik tezgahı (commit `2dfda9e`) | **18 PASS · 1 FAIL · 2 WARN** |
| SQLite bütünlüğü | `ok` |
| Şifreli hücre | 175 |

Temmuz 9 (commit `7f1951d`) → bugün: 19 PASS/1 FAIL/1 WARN → 18/1/2. **Gerileme var**,
aşağıda §5'te.

---

## 3. Beyaz şapka — gerçekten sağlam olanlar

Bunlar övgü değil, ölçümle geçmiş kalemler.

**3.1 İzin hesabı modelin dışında.** `gate.py` el yazması ve deterministik: bilinmeyen
araç, bilinmeyen argüman anahtarı, yanlış tip (`"20"` string reddedilir, `True` int
sayılmaz), aralık dışı — hepsi kod tarafından reddediliyor. Yedi `AUTHZ-*` kontrolünün
tamamı PASS. **Neden önemli:** 2026 sektör mutabakatı tam olarak bunu söylüyor —
"yetkilendirmeyi ajanın kendi kodunun geçemeyeceği bir sınırda uygula."

**3.2 Araç yüzeyi kasten dar.** Üç salt-okunur araç. Tek yazıcı (`kasa_note`) bayrağı
kapalı sevk ediliyor ve izni seed bile edilmiyor. **Sonuç:** tamamen ele geçirilmiş bir
model bile bu tavana çarpar. Savunmanın doğru yeri burası — modelin ne kadar dirençli
olduğu değil, ele geçirilince ne yapabileceği.

**3.3 Denetim zinciri kurcalamaya duyarlı ve bu test edilmiş.** `encrypt-then-hash`,
`AUDIT-TAMPER-MODIFY` ve `AUDIT-TAMPER-DELETE` PASS. Şifreli hücrenin tek karakteri
değiştirilince zincir bozuluyor — testle kanıtlı.

**3.4 Hücre şifrelemesi AAD ile bağlamına bağlı.** Satır/kolon takası `InvalidTag` ile
patlıyor (`test_aad_swap_breaks_decrypt`). Bu, çoğu "şifreli DB" iddiasının atladığı
inceliktir.

**3.5 Dürüst öz-raporlama.** Pano `full_db: SQLCipher, status: pending` diyor —
kurulmamış olanı kurulmuş göstermiyor. THREAT_MODEL rezidüelleri madde madde listeliyor.
Bu, projenin en değerli kültürel özelliği ve nadir.

**3.6 Ölçüm kültürü.** 21 güvenlik kontrolü + 6 aileli model tezgahı + canary'ler. Model
seçimi bile ölçümle yapıldı ve **başarısız çıkan kendi düzeltmesi dürüstçe kaydedildi**
(`MODEL_SECIMI_TR.md` §4.1: araç seçimi 50→50, hedef tutmadı).

---

## 4. Kırmızı şapka — saldırgan gözüyle, ölçülmüş yollar

### 4.1 BULGU-1 (yeni, ölçüldü): hız sınırı `agent_id` döndürerek tamamen baypas ediliyor

DEBİ-0 hız sınırlayıcısı kovaları `agent_id`'ye göre tutuyor. Ama `agent_id` **istek
gövdesinden geliyor ve istemci beyanlı** — THREAT_MODEL bunu zaten rezidüel olarak
listelemiş, ancak sınırlayıcı bu varsayımın üstüne kurulurken etkileşim not edilmemiş.

İzole ortamda ölçtüm (kullanıcı vault'una dokunmadan):

| Senaryo | İstek | 429 (fren) | Sonuç |
|---|---|---|---|
| Sabit `agent_id` | 150 | **90** (61.'den itibaren) | Fren tasarlandığı gibi çalışıyor |
| Dönen `agent_id` | 150 | **0** | Fren **hiç** devreye girmiyor |
| Dönen + audit ölçümü | 300 | **0** | Zincire **300 kalıcı satır** yazıldı |

**Sebep:** `RATE_LIMITER.allow(request.agent_id, ...)` — anahtar, doğrulanmış kimlik değil
**iddia edilen** kimlik.

**Sonuçlar (dördü birden):**
1. Sınırlayıcının yazılma gerekçesi olan senaryo — *"halüsinasyon döngüsüne giren ajan
   sınırsız çağrıyla audit zincirini doldurur"* — **hâlâ açık**. 300/300 yazıldı.
2. Kova sözlüğü sınırsız büyüyor (300 istek → 300 girdi). Kaynak tükenmesini engellemek
   için yazılan mekanizma **kendisi** ikinci bir kaynak deliği.
3. **Ajanlar arası DoS:** A ajanı `agent_id=B` diyerek B'nin kovasını tüketebilir.
4. **Audit atfı sahtelenebilir:** zincir "bu kayıt değişmedi" kanıtlar, "bunu şu ajan
   yaptı" kanıtlamaz. KURALLAR §7'nin garantisi kısmen boş.

**Şiddet — dürüst kalibrasyon:** saldırganın bearer token'a zaten sahip olması gerekiyor,
yani uzaktan kimliksiz bir delik **değil**. Ama KASA'nın modeli "her ajan MCP ile
bağlanır" olduğu için **token'ı zaten her ajan biliyor**. Sınırlayıcının işi, birçok ajan
arasından yaramaz olanı sınırlamaktı — ve tam o işi yapamıyor.

**Konjonktürel not:** 2026 mutabakatının dört maddesinden biri kelimesi kelimesine şu:
*"kimlik bilgilerini kanıtlanmış kimliklere bağla."* Bu bulgu, sektörün adını koyduğu
eksiğin KASA'daki tam karşılığı.

### 4.2 BULGU-2: at-rest metadata deseni (§1)

Bilinçli takas, ama bulut-senkron senaryosunda (THREAT_MODEL düşman C) etkisi
küçümsenmiş: DPAPI içeriği korur, **deseni korumaz**. OneDrive'a düşen bir `kasa.db`,
başka makinede açılamasa bile profil anahtarlarını ve gezinti ritmini ele verir.

### 4.3 BULGU-3: bearer token düz metin — ama şiddeti abartılmamalı

`kasa.toml:4` token'ı düz metin tutuyor. Tezgah bunu `critical` sayıyor.

**Karşı argüman (dürüstlük gereği):** token yalnız `127.0.0.1`'de işe yarar. Onu okuyabilen
bir saldırgan zaten aynı kullanıcı bağlamındadır ve aynı bağlamda DPAPI'yi çağırıp vault
anahtarını da alabilir. Yani token **ek** bir maruziyet getirmiyor.

ACL ölçümü: `SYSTEM + Administrators + <sahip-hesabı>` — sıradan ikinci bir OS kullanıcısı
dışarıda, yani düşman sınıfı B kapalı. **Değerlendirmem: bu `critical` değil, `low`.**
Tezgahın şiddet kalibrasyonu burada hatalı ve bu, §5'in konusu.

### 4.4 BULGU-4: egress yok

`GUVENLIK_CIKIS_PLANI.md` Faz 1–4 planlı, **hiçbiri kurulmadı**. 2026 mutabakatında
containment'ın dört ayağından biri "egress'i kontrol et" — ve neredeyse her büyük prompt
injection olayının ortak deseni şu üçlü: *özel veriye erişim + güvenilmez içeriğe maruz
kalma + dışarıyla konuşabilme*. KASA ilk ikisini sıkı yönetiyor, **üçüncüsünü hiç
ölçmüyor**.

### 4.5 Kapatılamayan (dürüst sınır)

Aynı kullanıcı bağlamındaki malware DPAPI'yi çağırabilir. Bellekteki düz metin
swap/hibernate ile pagefile'a düşebilir. İkisi de belgelenmiş, Python'da pratik
mitigasyonu yok. **Bunlar eksik değil, sınır** — ve doğru yerde yazılı.

---

## 5. En tehlikeli bulgu: kırmızı ışıklar güvenilirliğini kaybediyor

Bu, tek tek hatalardan daha ciddi çünkü KASA'nın gerçek farkı **ölçüm kültürü**.

| Gösterge | Durum | Neden sahte |
|---|---|---|
| `SCAN-SECRETS` | **FAIL critical** | Kanıt: *"Scan timed out"* — kontrol **koşmadı**. Koşamayan kontrol bulgu değildir. "Baktım, buldum" ile "bakamadım" aynı kırmızıya boyanıyor. |
| `SCAN-BANDIT` | WARN, Medium **6 → 13** | Üç haftada iki katına çıkmış, hiçbiri triyaj edilmemiş |
| `SCAN-BAK-HYGIENE` | WARN (yeni) | `src/distill/engine.py.bak` — 9 Temmuz'dan kalma artık |
| `selftest_rollback` | Sürekli FAIL | Sağlık raporu §2: mekanizma **çalışıyor**, test bayat yere bakıyor |
| `board.json` | `tracker-request-block-paranoid` = blocked | Sağlık raporu §4: iş **bitmiş**, testi 4 passed |
| Pano spinner'ları | Hep "çalışıyor" | Bugün düzeltildi — CSS `[hidden]` ezilmişti |

**Sebep:** her biri ayrı ve masum. **Sonuç birleşince tek:** insan kırmızıya bakmayı
bırakır. Gerçekten bozulduğu gün fark edilmez. Bu projede "mühür = ölçüm" kuralı var;
ölçüm aleti bozulursa mühür de boş kalır.

Bugün pano göstergesinde bunun canlı örneğini gördük: gösterge her durumda "Model
düşünüyor / Testler çalışıyor" diyordu, yani **hiçbir şey ölçmüyordu**.

---

## 6. Konjonktür — 2026'da KASA nerede duruyor

### 6.1 "Boş hücre" iddiası artık geçerli değil

`PROJECT_BRIEF.md` §2 (2 Temmuz) diyordu ki: *"tam ajansal + tam yerel + kullanıcıya ait
veri kombinasyonu büyük satıcılar tarafından esasen işgal edilmemiş."*

**Bu, bir ay içinde değişti.** Yerel-öncelikli ajan hafızası artık kalabalık bir kategori:
Mem0'ın OpenMemory'si MCP uyumlu yerel hafıza sunucusu olarak Claude Desktop / Cursor /
VS Code ile çalışıyor; `the-vault` ve `memory-vault` gibi açık projeler aynı işi yapıyor.
MCP, ajan-araç iletişiminde birinci sınıf standart hâline geldi ve hafıza katmanı bir MCP
sunucusu olarak sunuluyor.

**Ama fark hâlâ var, sadece yeri değişti.** Rakipler **hafıza katmanı**; KASA bir
**güvenlik katmanı** olarak hafıza tutuyor. Onlarda olmayan, KASA'da ölçülmüş olan:
şifreli kasa + izin brokerı + kurcalamaya duyarlı denetim zinciri + deterministik kapı.
Konumlandırma "yerel hafıza" değil, **"denetlenebilir hafıza"** olmalı. Bu, satılabilir
farkın nerede olduğunu da değiştirir: hız/kolaylık değil, **kanıt**.

### 6.2 Prompt injection: sektör "çözüm" beklemeyi bıraktı

2026 mutabakatı net: injection model seviyesinde çözülmüyor; gerçekçi hedef
**containment**. Dört ayak sayılıyor:

| Mutabakat maddesi | KASA |
|---|---|
| Ayrıcalığı asgariye indir | **✓** üç salt-okunur araç, yazıcı kapalı |
| Güvenilmez girdiyi sonuçlu eylemden ayır | **✓** sayfa içeriği veridir kuralı + UNTRUSTED marker |
| Egress'i kontrol et | **✗** planlı, kurulmadı |
| Ajanların ne yaptığını izle | **~** audit var, ama atıf sahtelenebilir (§4.1) |

Ayrıca Mayıs 2026'da Five Eyes (CISA, NSA ve BK/Kanada/Avustralya/Yeni Zelanda muadilleri)
ajansal AI için ortak rehber yayımladı; prompt injection'ı çekirdek manipülasyon yolu
olarak adlandırıyor ve **tek bir önlemin yetmediğini** vurguluyor. KASA'nın katmanlı
yaklaşımı bu rehberle uyumlu — eksik olan katman egress.

**Dürüst sonuç:** KASA kavramsal olarak sektörün doğru tarafında. Uygulama olgunluğunda
iki somut boşluk var: **kimlik bağlama** (§4.1) ve **egress** (§4.4). İkisi de sektörün
adını koyduğu maddeler; yani spekülatif değil, ısmarlama iş listesi.

---

## 7. Eksikler — önceliklendirilmiş

| # | Eksik | Sebep | Sonuç | Şiddet | Maliyet |
|---|---|---|---|---|---|
| E1 | Ölçüm aletleri sahte kırmızı üretiyor | timeout=FAIL, bayat test yolu, bayat pano | Kırmızıya güven biter; gerçek arıza görülmez | **Yüksek** | saatler |
| E2 | `agent_id` doğrulanmıyor → hız sınırı baypas | Kimlik istemci beyanlı | DEBİ-0 hedefi açık; audit atfı sahte; ajanlar arası DoS | **Yüksek** | 1 gün |
| E3 | Egress kontrolü yok | Kurulmadı (plan var) | Exfiltration normal trafikten ayırt edilemez | **Yüksek** | 2–3 gün (Faz 1+2) |
| E4 | At-rest metadata deseni açık | Sorgulanabilirlik zorunluluğu | Bulut-senkron kopyasından davranış profili çıkar | Orta | karar işi |
| E5 | Bandit Medium 6→13 triyaj edilmedi | Bakılmadı | Bilinmeyen büyüyor | Orta | saatler |
| E6 | Model araç seçimi zayıf (MB-TC-PICK 50) | Prompt'la kapanmadı, ölçüldü | Ajan yanlış aracı çağırıyor | Orta | F2/F3, günler |
| E7 | Ingest etiketleme kurulmadı | 6 açık soru sahip onayında | Zehirli içerik takibi yok | Orta | plan hazır |
| E8 | DPAPI Windows-only | Tasarım | macOS/Linux portu yok | Düşük | YAGNI |
| E9 | Bearer token düz metin | Config dosyası | Ek maruziyet ~yok (§4.3) | **Düşük** | dakikalar |
| E10 | `journal_mode=delete` (WAL değil) | Varsayılan | Eşzamanlı okuma/yazma gerekirse darboğaz | Düşük | dakikalar |
| E11 | PID dosyası canlılık kanıtı değil | Desen eksik | Çift-daemon riski | Düşük | saatler |

---

## 8. Projeksiyon — adımlarıyla

Sıralama ilkesi: **önce ölçüm aleti, sonra ölçtüğü şey.** Bozuk aletle yapılan her
düzeltme, düzeldiğini kanıtlayamaz.

### P0 — Ölçümü onar (önkoşul, ~yarım gün)

Her şeyden önce, çünkü sonraki fazların kabul kapıları bu aletlere bakacak.

1. `SCAN-SECRETS`: `timeout` durumunu **FAIL'den ayır** → yeni durum `ERROR`
   ("kontrol koşamadı"). Verdict hesabında `ERROR` ayrı sayılsın.
   *Kabul:* tezgah çıktısında hiçbir kalem "bakamadım"ı "buldum" gibi göstermiyor.
2. `selftest_rollback.py:59` → `.bak` aramasına `_bak_archive/` eklensin; ayrıca selftest
   **üretim arşivine yazmayı** bıraksın (geçici dizine yazsın).
   *Kabul:* selftest yeşil ve `_bak_archive/` koşu sonrası büyümüyor.
3. `board.json`: `tracker-request-block-paranoid` → yeşil. `blocked` yazan kod yoluna
   **sebep zorunluluğu** (sebepsiz blocked yazılamasın).
   *Kabul:* panoda sebepsiz `blocked` bulunmuyor.
4. `src/distill/engine.py.bak` sil; Bandit'in 13 Medium'unu triyaj et (her biri: gerçek /
   kabul edilmiş / yanlış-pozitif + gerekçe).
   *Kabul:* `SCAN-BAK-HYGIENE` PASS, Bandit bulguları gerekçeli listede.

**Faz çıktısı:** `docs/SECURITY_BENCHMARK.md` yeniden koşar, her kalem ya PASS ya
gerekçeli.

### P1 — Kimlik bağlama (E2, ~1 gün)

Sektörün adını koyduğu eksik + bugün ölçtüğüm delik.

1. **Ajan başına token.** `permissions` tablosuna `agent_token_hash` (veya ayrı
   `agent_tokens` tablosu). Kayıt sahibin işi (owner-gated), ağdan yapılamaz.
2. `verify_token` → **token'dan agent_id çöz**. `request.agent_id` artık kimlik değil,
   yalnız log alanı; **uyuşmazsa 403**.
3. `RATE_LIMITER.allow(...)` → çözülmüş kimlikle çağrılsın, iddia edilenle değil.
4. Kova sözlüğüne **üst sınır** (LRU veya kapasite + en eski düşer).
5. `audit_chain.record(...)` → doğrulanmış kimliği yazsın.
6. Geçiş: tek-token modu bir sürüm daha desteklensin (`legacy_shared_token`), uyarı
   loglasın.

*Kabul kapısı (bugünkü prob yeniden koşar):* dönen `agent_id` ile 300 istek → **429
devreye giriyor**, audit'e 60'tan fazla satır yazılmıyor, kova girdisi sınırlı.

### P2 — Egress kapısı (E3, ~2–3 gün)

`GUVENLIK_CIKIS_PLANI.md` Faz 1 + Faz 2 zaten yazılı; kurulacak.

1. **Faz 1:** `kasa_egress.py` yerel proxy; her istek JSONL kayıt defterine (ts, görev-id,
   host, port, izin/engel, sebep, byte). Görev-bazlı allowlist; dışı = ENGEL + bayrak.
   *Kabul:* izinli host geçer, ekli sahte-sızıntı host'u **engellenir**.
2. **Faz 2 (projenin özgün farkı):** OS-seviyesi bağımsız görünüm
   (`Get-NetTCPConnection`/pktmon) proxy'den habersiz toplansın; deterministik mutabakat
   **(OS gözlemi) − (proxy izinlisi) = ∅**.
   *Kabul:* proxy'yi baypas eden ekli test-bağlantısı mutabakatta **yakalanır**.
3. Faz 3 (giriş anomalisi) ve Faz 4 (TLS MITM) **ayrı karar** — Faz 4 invaziv, CA
   sertifikası gerektiriyor, sahip onayı şart.

*Neden bu sırada:* egress olmadan §6.2'deki dört ayaktan biri boş kalıyor ve exfiltration
ölçülemiyor.

### P3 — At-rest metadata kararı (E4, karar işi)

Bu bir kod işi değil, **karar** işi. Üç seçenek, hepsi meşru:

| Seçenek | Kazanç | Bedel |
|---|---|---|
| (a) Kabul et, belgele | sıfır maliyet, mevcut durum | bulut-senkron kopyası deseni ele verir |
| (b) `profile.key` için blind-index | anahtar adları gizlenir, eşitlik sorgusu çalışır | şema + migrasyon; aralık sorgusu gider |
| (c) Tam-DB şifreleme (OS/BitLocker veya SQLCipher) | metadata dahil her şey kapanır | SQLCipher bu makinede infeasible (wheel+derleyici yok); BitLocker OS kararı |

**Önerim:** (a) + (c-hafif) — yani mevcut mimariyi koru, ama kuruluma *"vault dizinini
şifreli birime koy"* adımı ekle ve panoda **`full_db` durumunu gerçek disk şifreleme
durumundan oku** (şu an sabit "pending" yazıyor). Böylece kullanıcı kapatabildiği bir
açığı kapatır, biz de yanlış beyan etmemiş oluruz. THREAT_MODEL'deki tripwire zaten
"içerik kolonunda WHERE/LIKE gerekirse yeniden aç" diyor — o koşul **gerçekleşmedi**.

### P4 — Model F2/F3 (E6, günler, GPU)

Ölçüm bu fazın gerekliliğini zaten kanıtladı (araç seçimi 50→50, prompt yetmedi).
`gate.chat_tool_schemas()` + `gate.validate_call` ile veri **deterministik üretilebilir**;
etiketi doğrulayıcı koyar. Kabul kuralı belgede yazılı ve korunmalı: **`MB-INJ-A1` PASS'tan
FAIL'e düşerse ince ayar reddedilir**, araç metrikleri ne kadar iyileşirse iyileşsin.

### P5 — Ingest etiketleme (E7, sahip kararı bekliyor)

`INGEST_LABELING_PLAN_TR.md` v4 hazır, §11'de **6 açık soru** var (plaintext
`ingest_labels` kolonu, maliyet asimetrisi oranı, "bağımsız köken" tanımı, bekleyen-terfi
TTL'i, kaynak başına kota, temel kademe dilleri). Bunlar cevaplanmadan kod yazılmamalı —
çünkü hepsi şemayı etkiliyor.

### P6 — Küçük borçlar (E5/E9/E10/E11, saatler)

Bearer token'ı DPAPI-wrap et (ucuz, tutarlılık için), `journal_mode=WAL` değerlendir,
PID → heartbeat'li kilit (deseni WebAjans'ta çözülmüş).

---

## 9. Özet — tek paragraf

KASA'nın **mimarisi doğru yerde**: izin kararı modelin dışında, araç yüzeyi kasten dar,
denetim zinciri kurcalamaya duyarlı ve test edilmiş, içerik at-rest gerçekten şifreli,
sınırlar dürüstçe yazılı. 2026 containment mutabakatının dört ayağından ikisini sağlam
tutuyor. **İki somut boşluk var** ve ikisi de sektörün adını koyduğu maddeler: kimlik
kanıtlanmış kimliğe bağlanmıyor (ölçüldü: hız sınırı 300/300 baypas edildi), ve egress
hiç ölçülmüyor. **En tehlikeli bulgu ise bunların hiçbiri değil:** ölçüm aletleri sahte
kırmızı üretmeye başladı, ve bu projenin gerçek farkı ölçüm kültürü olduğu için, önce o
onarılmalı.

---

<!-- Denetim: Claude (Opus 5), 2026-08-01. Tüm ölçümler bu makinede fiilen koşturuldu;
     saldırı denemeleri izole geçici KASA_HOME'da yapıldı, kullanıcı vault'una dokunulmadı.
     Konjonktür bölümü web araştırmasıyla dayanaklandırıldı (kaynaklar sohbet kaydında). -->
