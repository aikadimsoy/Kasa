# KASA Öğretim Çerçeve Programı

> **Ölçülene kadar mühürlenmez.** Bu belge de o kurala tabidir: içindeki her teknik iddia
> ya depodaki bir dosyaya (yol + satır) ya da tarihli bir ölçüm damgasına dayanır.
> Dayanağı olmayan cümle yazılmadı.

| Alan | Değer |
|---|---|
| Belge sürümü | v1.0 (öneri — sürüm numarası AI tarafından *önerilir*, sahip tarafından *ilan edilir*; `KURALLAR.md` §2) |
| Tarih | 2026-08-03 |
| Durum | TASLAK — sahip onayı bekliyor (`KURALLAR.md` §1/T1) |
| Kapsam | KASA deposunda birikmiş mimari, güvenlik ve ölçüm bilgisinin öğretim programına dönüştürülmüş hâli |
| Hedef kitle | (1) Yerel-öncelikli/gizlilik odaklı yazılım geliştiricileri, (2) ajan (LLM) sistemleri kuran mühendisler, (3) güvenlik değerlendirmesi yapan denetçiler, (4) lisansüstü ders/seminer yürütücüleri |
| Ön koşul (genel) | Python okuryazarlığı, SQL temel, komut satırı; kriptografi ön bilgisi gerekmez |
| Dil | Türkçe (teknik terimler İngilizce karşılıklarıyla) |
| Lisans | Program materyali KASA ile aynı lisans altındadır: **AGPL-3.0** (`LICENSE`). Ticari eğitim seçeneği için bkz. §9 |
| Platform gerçeği | Laboratuvarların çoğu Windows'a bağlıdır (DPAPI); bkz. §10 |

---

## 0. Bu belgeyi nasıl okumalı

Program üç katmandan oluşur ve katmanlar birbirinin yerine geçmez:

1. **Envanter (§3)** — *ne biliniyor*. KASA'nın bilgi birikiminin kategorik dökümü, her
   maddenin depodaki karşılığıyla.
2. **Müfredat (§4)** — *nasıl öğretilir*. Modüller, süreler, laboratuvarlar, ölçütler.
3. **Patikalar (§5)** — *kime, ne kadar*. Aynı malzemenin üç farklı yoğunlukta kurgusu.

Atıflar (§7) iki sınıfa ayrılmıştır ve karıştırılmamalıdır: **iç atıflar** bu depodaki
gerçek dosyalardır (yazılmadan önce varlıkları kontrol edildi); **dış atıflar** yerleşik
kaynaklardır ve künyesinden emin olunmayanlar `[DOĞRULANMALI]` etiketiyle işaretlenmiştir.

---

## 1. Vizyon

### 1.1 Neden böyle bir program?

Ajan (agent) tabanlı yazılım, 2026'da kişisel verinin ana işlenme yüzeyi hâline geldi.
Bu geçişte üç şey aynı anda oldu: (a) kalıcı kullanıcı hafızası satıcı bulutlarına taşındı,
(b) yetkilendirme kararları giderek modelin kendisine devredilmeye başlandı, (c) güvenlik
iddiaları ölçüm yerine pazarlama diliyle kuruldu.

KASA bu üç eğilime karşı somut bir karşı-örnek olarak inşa edildi. Ama bir karşı-örneğin
değeri, yalnızca çalışmasında değil, **aktarılabilir olmasında**dır. Bu program o aktarımı
yapar.

Programın dayandığı üç kültürel taahhüt:

- **Kişisel yapay zekâ egemenliği.** Kullanıcının hafızası kullanıcının makinesinde durur;
  ajanlar bu hafızaya *izin aracılığıyla* erişir. Tez tek cümledir: *"Ajanlar gelir geçer;
  hafızan senindir."* (`README.md`, `docs/PROJECT_BRIEF.md` §1)
- **Veri sahipliği bir mimari özelliktir, bir politika metni değildir.** "Unutma"nın gerçek
  olması, ham kopyaların TTL sonrası fiilen silinmesine bağlıdır — sözleşmeye değil
  (`docs/PROJECT_BRIEF.md` §6.1, `src/mcp_server/tools.py:158`).
- **Ölçüm-dürüstlüğü kültürü.** Bu, programın ayırt edici parçasıdır. KASA'nın kendi
  belgeleri, hedeflenen düzeltmenin **tutmadığını** kaydeder (`docs/MODEL_SECIMI_TR.md`
  §4.1: araç seçimi 50 → 50), kendi ölçüm aletinin ürettiği **yanlış kırmızıyı** bulgu
  saymaz (`docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md` §1 "Ölçüm dürüstlüğü notu"), ve
  bir denetim raporu kendi önceki iddiasını geri alır
  (`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §0). Bu davranış öğretilebilir bir
  beceridir ve yazılım güvenliği eğitiminde nadiren öğretilir.

### 1.2 Programın iddiası ve iddia etmediği

**İddia:** Bu programı tamamlayan kişi, yerel-öncelikli bir ajan sisteminin güvenlik
sınırlarını *kurabilir*, o sınırların çalıştığını *ölçebilir* ve ölçüm aletinin kendisinin
bozulup bozulmadığını *sınayabilir*.

**İddia etmediği:** Bu program kişiyi "güvenli sistem kurmuş" yapmaz. KASA'nın kendisi
mühürlü değildir; iki somut boşluğu ölçülmüş ve yazılıdır (kimlik bağlama, egress —
`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §9). Program bu boşlukları gizlemek yerine
**ders malzemesi olarak kullanır**: açık bir sistemin nasıl dürüstçe belgelendiğini
göstermek, kapalı bir sistemin nasıl övüldüğünü göstermekten daha öğreticidir.

---

## 2. Hedefler — ölçülebilir öğrenme çıktıları

Çıktılar Bloom benzeri fiillerle yazılmıştır (tanımlar → ayırt eder → uygular → çözümler →
ölçer → eleştirir → tasarlar). Her çıktı "programı bitiren kişi X yapabilir" biçimindedir
ve §4'te bir değerlendirme ölçütüne bağlanır.

### Seviye 1 — Tanır ve ayırt eder

- **Ç1.1** Yerel-öncelikli (local-first) mimariyi bulut-öncelikli mimariden, *veri sahipliği*
  ve *çalışabilirlik* eksenlerinde **ayırt eder**.
- **Ç1.2** "Model güvenlik sınırı değildir" ilkesini **tanımlar** ve bir mimaride sınırın
  nerede olduğunu (deterministik kod mu, prompt mu) **gösterir**.
- **Ç1.3** Veri ile talimatı **ayırt eder**; bir sistemde web/dış kaynak metninin hangi
  noktada "komut" hâline geldiğini **işaretler**.
- **Ç1.4** Tamper-**evident** (tahrif *belli olur*) ile tamper-**proof** (tahrif *olamaz*)
  arasındaki farkı **tanımlar** ve hash zincirinin hangisi olduğunu **söyler**.
- **Ç1.5** `FAIL` (ölçtüm, sorun buldum) ile `ERROR` (ölçemedim) durumlarını **ayırt eder**
  ve ikisini aynı renge boyamanın sonucunu **açıklar**.

### Seviye 2 — Uygular

- **Ç2.1** Hücre başına AES-GCM şifreleme **uygular**; AAD'yi hücrenin bağlamına
  **bağlar** ve satır/kolon takasının neden çözmeyi bozduğunu **gösterir**.
- **Ç2.2** Deny-by-default bir izin tablosu **kurar**; kapsam (scope) hesabını
  deterministik kodda **uygular**, modele **bırakmaz**.
- **Ç2.3** Hash-zincirli denetim kaydı **yazar**; checkpoint + arşiv ile zinciri kırmadan
  büyümeyi **sınırlar**.
- **Ç2.4** Güvenilmez metni bir prompt'a koymadan önce yapısal olarak **nötralize eder**
  (delimiter breakout savunması).
- **Ç2.5** Bir yerel modeli tekrar-üretilebilir bir tezgahta **ölçer** ve sonucu tarihli bir
  damgaya **yazar**.

### Seviye 3 — Çözümler ve ölçer

- **Ç3.1** Bir izin kapısını canlı saldırıyla **sınar**; red nedenlerini HTTP durum koduna
  göre **sınıflandırır** (401 kimlik / 403 kapsam / 404 ad-uzayı / 429 debi / 422 şema).
- **Ç3.2** Bir maskeleme (redaction) kuralının yanlış-pozitif ve yanlış-negatif oranını
  gerçek korpus üzerinde **ölçer**; eşiği ölçüme dayanarak **kalibre eder**.
- **Ç3.3** Şifreli kolonlara hiç dokunmadan, yalnız düz metin metadata'dan bir davranış
  profili **çıkarır** ve bunun mahremiyet sonucunu **raporlar**.
- **Ç3.4** Bir hız sınırlayıcının kimlik döndürerek baypas edilebildiğini **ölçer** ve kök
  nedeni ("kimlik doğrulanmıyor") semptomdan ("fren tutmuyor") **ayırır**.

### Seviye 4 — Eleştirir ve tasarlar

- **Ç4.1** Bir ölçüm aletinin **yanlış-PASS** ve **yanlış-FAIL** üretebileceği yolları
  **avlar**; her kontrol için pozitif ve negatif kontrol **tasarlar**.
- **Ç4.2** Bir güvenlik belgesini ev kurallarına karşı **denetler**; ölçüm referansı
  olmayan mutlak iddiaları **işaretler** ve ölçüye dayalı hâline **yeniden yazar**.
- **Ç4.3** Bir mimari kararı sebep → karar → sonuç formatında **kaydeder** (ADR) ve
  reddettiği alternatifin bedelini **yazar**.
- **Ç4.4** Bir tehdit modeli **üretir**: düşman sınıfları, savunmalar ve **rezidüel
  riskler** — rezidüeli gizlemeden.
- **Ç4.5** Bir "kabul kapısı" **tasarlar**: hangi ölçüm hangi eşikte düşerse iş
  **reddedilir** (ör. ince ayar sonrası enjeksiyon direnci düşerse ince ayar reddedilir —
  `docs/MODEL_SECIMI_TR.md` §6).

---

## 3. Kategorik envanter

On kategori. K1–K8 sahibin önerdiği çerçevedir; **K9 ve K10 eklendi** çünkü depoda bu iki
gövde ayrı ve tutarlı bir bilgi kümesi olarak mevcuttur (debi kontrolü tek belgede
toplanmıştır: `docs/FLOW_CONTROL_TR.md`; yönetişim/karar kaydı ise `docs/adr/` +
`KURALLAR.md` ikilisiyle bağımsız bir disiplindir).

Zorluk seviyeleri: **T** temel · **O** orta · **İ** ileri.

---

### K1 — Yerel-öncelikli mimari ve veri egemenliği · **T–O**

**Ön koşul:** yok.

| Konu | KASA'daki karşılığı |
|---|---|
| Local-first tezi, "ince kenar / kalın çekirdek" değişmezi | `docs/PROJECT_BRIEF.md` §4 (Değişmez 1) |
| Koşullu-entropi saklama ilkesi `Store(D) ≈ H(D\|M)` | `docs/PROJECT_BRIEF.md` §3.1 |
| Üç hafıza kademesi (ham olay / damıtılmış profil / taşınabilir ihraç) | `docs/PROJECT_BRIEF.md` §6.1; `src/vault/schema.py` |
| TTL ve gerçek silme; `forget()` (belgede "garanti" olarak adlandırılan davranış — `docs/PROJECT_BRIEF.md` §6.1) | `src/mcp_server/tools.py:158`, `src/vault/database.py:191` (`PRAGMA secure_delete=ON`) |
| Şifreli taşınabilir ihraç (scrypt + AES-GCM) | `src/export/encrypt.py:27` |
| Loopback-only ağ duruşu | `src/mcp_server/server.py:241`, `docs/UI_UX_STANDARD.md` §2.1 |
| MVP kapsam disiplini (eylem katmanı bilinçli olarak dışarıda) | `docs/PROJECT_BRIEF.md` §8 |

**Öğretici çekirdek:** "Yerel" bir konum değil bir **sözleşmedir**; sözleşmenin kanıtı
ağ duruşu, silme davranışı ve ihraç formatıdır.

---

### K2 — Kriptografi uygulaması · **O–İ**

**Ön koşul:** K1.

| Konu | KASA'daki karşılığı |
|---|---|
| Hücre başına AES-256-GCM, `K1:` önekli ciphertext | `src/vault/cell_crypt.py:46`, `:56` |
| AAD ile bağlam bağlama (tablo\|kolon\|bağlam) — takas saldırısı savunması | `src/vault/cell_crypt.py:67`, `:71`, `:76`; test: `tests/test_l2_at_rest.py` |
| DPAPI anahtar koruması (`CryptProtectData`), KeyProvider dikişi | `src/vault/encryption.py`, `src/vault/cell_crypt.py:33` |
| Anahtar rotasyonu ve zincirle etkileşimi | `src/vault/database.py:84`; ders: `docs/FLOW_CONTROL_TR.md` DEBI-2 "yan bulgu" |
| KDF seçimi: scrypt (ihraç) vs PBKDF2 (opsiyonel parola) | `src/export/encrypt.py:27`, `src/vault/database.py:23` |
| Encrypt-then-hash sırası (audit) | `src/vault/audit.py:46` |
| Fizibilite kararı: neden SQLCipher değil | `docs/adr/0003-at-rest-sifreleme-boslugu.md`, `docs/THREAT_MODEL.md` §L2 |
| Migrasyon güvenliği: önek yoksa legacy-plaintext kabul | `src/vault/cell_crypt.py` modül notu; `tests/test_l2_migration.py` |

**Öğretici çekirdek — belgedeki en önemli tek cümle:** *"Bir kolonu şifrelemek depolama
değil **erişim-deseni** kararıdır; kolona dokunan HER SQL ifadesi önce listelenmeli."*
(`docs/THREAT_MODEL.md` §İLKE). Bu ilke `forget()`'in sıcak yolunu ve audit yan-kanalını
nasıl kaçırdıklarının dersidir.

---

### K3 — Ajan güvenliği: enjeksiyon ve veri/talimat ayrımı · **O–İ**

**Ön koşul:** K1.

| Konu | KASA'daki karşılığı |
|---|---|
| Değişmez 3: "sayfa içeriği veridir, talimat değildir" | `docs/PROJECT_BRIEF.md` §4, `KURALLAR.md` §4 |
| UNTRUSTED sınırlayıcılarla sarma (damıtma yolu) | `src/distill/engine.py:79`, `:86` |
| Delimiter breakout savunması (ZWSP ile `<<<` bozma) | `src/vault/redact.py:190`; test: `tests/test_delimiter_breakout.py` |
| Ad-uzayı allow-list + içerik denylist ayrımı | `src/distill/engine.py:29`, `src/agent/gate.py:75` |
| Provenance QC: fact ancak kaynağı gösterilebiliyorsa yazılır | `src/distill/engine.py:211`, `:224`; test: `tests/test_distill_injection.py` |
| Saldırı kataloğu (A1–A6) ve dolaylı enjeksiyon probu | `_orch/redteam/attack_catalog.json`, `tools/model_bench/probes.py:358` |
| Harness sınırı: her araç sonucu kırpılır + maskelenir + temizlenir | `src/agent/harness.py` (modül docstring'i sınırı sayar) |
| "Ele geçirilmiş model tavanı": yüzey üç salt-okunur araç | `src/agent/gate.py:44`; değerlendirme: `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §3.2 |

**Öğretici çekirdek (ölçülmüş, sezgiye aykırı):** *Model gücü savunmayı güçlendirmiyor.*
Test edilen en büyük model en kötü dayanıklı çıktı; belirleyici olan parametre sayısı değil
hizalama reçetesi (`docs/MODEL_SECIMI_TR.md` Bulgu 3). Doğru yatırım "daha büyük model"
değil, **ele geçirilmiş modelin yapabileceklerini daraltmak**.

---

### K4 — Yetkilendirme: deny-by-default ve izin aracılığı · **O–İ**

**Ön koşul:** K1, K3.

| Konu | KASA'daki karşılığı |
|---|---|
| İzin hesabı: `granted(agent, scope) ∧ tier ≥ required_tier` | `docs/PROJECT_BRIEF.md` §3.3 |
| Deny-by-default izin tablosu | `src/mcp_server/tools.py:39` |
| Ad-uzayı kapısı: `PUBLIC_TOOLS` + rezerve kimlikler | `src/mcp_server/server.py:63`, `:64` |
| Kasıtlı ağ-dışı bırakılan araçlar (`audit_checkpoint`, `audit_archive`) | `src/mcp_server/server.py:67` yorumu; `src/mcp_server/tools.py:262`, `:276` |
| Deterministik argüman kapısı: tip/aralık/uzunluk, `bool` ≠ `int` | `src/agent/gate.py:85` (özellikle `:115`) |
| Bütçe sabitleri (iterasyon, duvar saati, karakter) | `src/agent/gate.py:25`–`:34` |
| Sahip CLI'si; `system` ve `admin:grant` bilerek verilemez | `tools/grant_agent_scope.py` |
| MCP izin aracılığı (adaptör sunucuya sıfır değişiklik getirir) | `src/mcp_adapter/proxy.py`, `docs/AGENT_BRIDGE.md` "Parçalar" §1 |
| Özerklik kademeleri T0–T3 ve eylem sınıfları A0–A3 | `docs/PROJECT_BRIEF.md` §6.3, §7; `KURALLAR.md` §6 |

**F-IMP kök nedeni — bu kategorinin ana vakası.** `agent_id` istemci-beyanlıdır ve
`RESERVED_AGENT_IDS` yalnız `{"system"}` içerir (`src/mcp_server/server.py:63`). `browser`
kimliği rezerve *değildir* ama başlangıçta `events:write` izni otomatik verilir
(`src/mcp_server/server.py:81`–`:84`). Token'ı olan bir saldırgan `agent_id="browser"`
diyerek bu izni devralır — izole sunucuda ölçüldü, `event_ingest` **HTTP 200** döndü
(`docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md` §2 F-IMP). **Ders:** kimlik *doğrulanmadan*
kurulan her kapsam hesabı, kimlik katmanının gücü kadardır.

---

### K5 — Denetlenebilirlik: hash zinciri, tahrif tespiti, atıf sorunu · **O**

**Ön koşul:** K2.

| Konu | KASA'daki karşılığı |
|---|---|
| Hash zinciri: her kayıt öncekinin özetini taşır | `src/vault/audit.py:46`, `:28` |
| Doğrulama ve tahrif tespiti | `src/vault/audit.py:95`; ölçüm: `docs/SECURITY_BENCHMARK.md` (AUDIT-TAMPER-MODIFY/DELETE) |
| Checkpoint ile mühürleme + yalnız mühürlü aralığın arşivi | `src/vault/audit.py:143`, `:166`; `docs/FLOW_CONTROL_TR.md` DEBI-2 |
| Sahte tohum reddi (mühürle eşleşmeyen `previous_hash` doğrulamayı düşürür) | `tests/test_flow_control.py` |
| Reddin de kaydı: sessiz ret kapatıldı (C2-GAP) | `docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md` §2.6; `src/mcp_server/tools.py:240`, `:299` |
| Köken koruyan mezar taşı (tombstone) vs gerçek silme | `src/mcp_server/tools.py:315`–`:326`; `docs/FLOW_CONTROL_TR.md` DEBI-3 |
| Saldırgan günlüğü ile savunucu audit'ini uzlaştırma | `_orch/redteam/persistent_attacker.py`, `_orch/redteam/attacker_journal.jsonl` |

**Atıf sorunu — bu kategorinin dürüstlük dersi.** Zincir *"bu kayıt değişmedi"* kanıtlar;
*"bunu şu ajan yaptı"* kanıtlamaz — çünkü `agent_id` istemci-beyanlıdır
(`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §4.1). Ayrıca hash zinciri
tamper-**evident**'tir, tamper-**proof** değil: tüm zinciri ileri yeniden hesaplayan
saldırgana karşı koruma checkpoint/dış çapaya bağlıdır ve **bu test edilmemiştir**
(`docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md` §2.5).

---

### K6 — Ölçüm bütünlüğü metodolojisi · **İ** — *programın ayırt edici kısmı*

**Ön koşul:** en az bir uygulama kategorisi (K2/K4/K5) tamamlanmış olmalı; bu kategori
"neyi ölçtüğünü" bilmeyen kişiye anlamsız gelir.

| Konu | KASA'daki karşılığı |
|---|---|
| Yanlış-PASS avı: geçerli JSON ama boş çıktı PASS sayıldı → verim ölçütü eklendi | `docs/MODEL_SECIMI_TR.md` §1.1; `tools/model_bench/probes.py:313` (MB-JSON-YIELD) |
| Yanlış-FAIL avı: açıkça reddeden model "çökmüş" sayıldı → notlama düzeltildi | `docs/MODEL_SECIMI_TR.md` §1.1 |
| Aletin negatif kontrolü: "zincir bozuk" denen şey aletin thread hatasıydı | `docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md` §1 |
| Pozitif kontrol: sistem gerçekten *ayırıyor* mu, yoksa her şeye mi hayır diyor | aynı belge §2.5 (yetkili 200 vs yetkisiz 403) |
| Üçüncü durum: `ERROR` ≠ `FAIL`; "ölçemedim" ayrı sayılır | `tools/security_bench/checks/scan.py:92`, `tools/security_bench/report.py:15`–`:22` |
| `DOĞRULANMADI` verdict'i (kapsam eksik) | `tools/security_bench/report.py:33` |
| Kapsam beyanı: kaç kontrol koştu / ne tarandı | `docs/SECRET_SCAN_CORPUS.md`; test: `tests/test_bench_scan_scope.py` |
| Drift: dünkü PASS bugün yalan olabilir (WebView2/config/OS damgası) | `tools/drift_canary.py`; `docs/drift_baseline.json` |
| Beklenti etiketi: `expect="defended"` ≠ `expect="open"` | `_orch/redteam/live_mcp_attack.py` modül docstring'i |
| Ölçen ≠ düzelten ayrımı | `docs/adr/0002-guvenlik-benchmark-kanit.md` |
| Kabul kuralı: hangi ölçüm düşerse iş reddedilir | `docs/MODEL_SECIMI_TR.md` §6 |
| "Sahte kırmızı" birikiminin insan etkisi | `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §5 |
| Alan taraması: her olgun mühendislik alanının "ölçemedim" durumu | `docs/OLCUM_BUTUNLUGU_VIZYON_2026-08-02.md` §4 |
| Kendi çerçevesini çürütme (yanlış-alarm yönü) | aynı belge §2, §8 |

**Öğretici çekirdek:** Dedektörün iki arıza modu vardır — sinyal *vermemesi* (sessiz arıza)
ve *yersiz vermesi* (yanlış alarm). KASA'nın kendi vaka listesinde **vakaların yarısı yanlış
alarmdı** (`docs/OLCUM_BUTUNLUGU_VIZYON_2026-08-02.md` §2). Watchdog/dead-man's-switch gibi
karşı-önlemler yalnız birinci yönü kapatır. Bu asimetri, güvenlik araç zincirlerinde
neredeyse hiç öğretilmez.

---

### K7 — Yerel model operasyonu · **O**

**Ön koşul:** K3.

| Konu | KASA'daki karşılığı |
|---|---|
| Model seçimini ölçümle yapmak (6 prob ailesi) | `tools/model_bench/probes.py`, `tools/model_bench/run.py` |
| Tezgahın üretim kodunu kullanması (kopya mantık yazmaması) | `docs/MODEL_SECIMI_TR.md` §1 |
| Enjeksiyon direnci ölçütü ve `heuristic` işaretlemesi | `tools/model_bench/probes.py:333`, `:358` |
| `format:"json"` yetmiyor, **şema kısıtı** gerekiyor | `docs/MODEL_SECIMI_TR.md` Bulgu 4; `src/distill/engine.py:48`, `:183` |
| Modelfile ile paketleme (`num_ctx`, `repeat_penalty`) | `models/kasa-agent.Modelfile`; `docs/MODEL_SECIMI_TR.md` §4.1 |
| Konfigürasyon birleştirme (üç dosya çelişiyordu) | `src/agent/store.py:111` (`resolve_model`), `src/distill/engine.py:14` |
| Tek-koşu gürültüsü ile tekrarlanan kategorik sonuç ayrımı | `docs/MODEL_SECIMI_TR.md` Bulgu 2, §5 |
| Tarihli model damgaları | `docs/MODEL_BENCH_hermes3-8b.md`, `docs/MODEL_BENCH_kasa-agent-8b.md`, `docs/MODEL_BENCH_qwen2.5-7b.md`, `docs/MODEL_BENCH_qwen2.5-3b.md` |

**Öğretici çekirdek:** Karar dayanağı **skor farkı değildir**. 78.1 vs 75.4 tek koşu
gürültüsü içindedir; dayanak, üç hafta arayla ve farklı notlama yöntemiyle **tekrarlanan**
kategorik A1 sonucudur (`docs/MODEL_SECIMI_TR.md` Bulgu 2). Aynı belge, bu ölçütü kendi
lehine bozmayı da reddeder: 84.2 vs 78.1 artışı da gürültü sayılır (§4.1).

---

### K8 — Mahremiyet mühendisliği: redaction, entropi, metadata · **O–İ**

**Ön koşul:** K2.

| Konu | KASA'daki karşılığı |
|---|---|
| Shannon entropisi ve eşik seçimi (4.3 bit/karakter) | `src/vault/redact.py:19`, `:63` |
| Base64 kuralına entropi tabanı (4.0) — kendine-DoS önleme | `src/vault/redact.py:26`, `:100` |
| Yapısal önek kalkanı (`AKIA…`, `ghp_…`, `sk_live_…`) — düşük entropili sırlar | `src/vault/redact.py:49` |
| Hex için bağlam koşulu (git-SHA yanlış-pozitifini önleme) | `src/vault/redact.py:78`, `:109` |
| URL'de cerrahi tarama: host/path korunur, query değeri taranır | `src/vault/redact.py:146` |
| Maskele-reddetme ayrımı (aşırı red = kendine-DoS) | `src/vault/redact.py` modül docstring'i |
| Read-through-redact sınırı (pano) | `src/dashboard/stats.py`; `docs/UI_UX_STANDARD.md` §2.2 |
| Dürüst metrik tasarımı: `masked_markers` vs `live_secrets_found` | `src/dashboard/stats.py` modül docstring'i |
| **Metadata sızıntısı** — içerik gizli, desen açık | `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §1 |
| Kalibrasyon borcunun açıkça yazılması | `src/vault/redact.py:11`–`:12` |

**Öğretici çekirdek:** Ölçülmüş bulgu — şifreli kolonlara **hiç dokunmadan**, yalnız düz
metin metadata'dan bir davranış profili çıkarılabildi: profil anahtarları, olay sayıları,
oturum penceresi (`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §1). Sebep zorunludur
(indeks, TTL taraması, hash zinciri sorgulanabilir kolon ister). Ders: mahremiyet kararı
şifreleme kararı **değildir**; sorgu deseni kararıdır.

---

### K9 — Kaynak yönetimi ve debi kontrolü · **O** *(eklendi)*

**Ön koşul:** K4, K5.

| Konu | KASA'daki karşılığı |
|---|---|
| Ajan başına token-bucket; izin kontrolünden **önce** uygulanır | `src/mcp_server/ratelimit.py:43`, `src/mcp_server/server.py:152` |
| Kova tahliyesi ve sert tavan (`max_buckets`) | `src/mcp_server/ratelimit.py:30`; test: `tests/test_ratelimit_eviction.py` |
| Anahtarlı özet ile tekilleştirme (HMAC; düz SHA-256 neden değil) | `src/mcp_server/tools.py:386`; `docs/FLOW_CONTROL_TR.md` DEBI-1 |
| Tekrar sayısının sinyale dönüşmesi (`occurrence_count` → damıtma) | `src/mcp_server/tools.py:398` |
| Sınırsız büyüyen zincire çıkış kapısı (checkpoint + arşiv) | `docs/FLOW_CONTROL_TR.md` DEBI-2 |
| Köken zinciri koruyan prune | `docs/FLOW_CONTROL_TR.md` DEBI-3 |

**Öğretici çekirdek:** Kaynak tükenmesini engellemek için yazılan mekanizmanın **kendisi**
ikinci bir kaynak deliği olabilir: 300 dönen kimlik → 300 kalıcı kova, tahliye yok
(`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §4.1). Savunma eklerken savunmanın
maliyet fonksiyonunu da ölç.

---

### K10 — Yönetişim, karar kaydı ve sürdürülebilirlik · **T–O** *(eklendi)*

**Ön koşul:** yok (ama K6 ile birlikte okunmalı).

| Konu | KASA'daki karşılığı |
|---|---|
| Ev kuralları: onay, sürüm, müdahale eşiği, güvenlik sınırları | `KURALLAR.md` |
| Dürüstlük kuralı: ölçüm referansı olmadan mutlak iddia yasak | `docs/UI_UX_STANDARD.md` §2.6 |
| ADR disiplini: sebep → karar → sonuç, reddedilenin bedeliyle | `docs/adr/0001`, `0002`, `0003` |
| Kırık vaadin raporlanması (düzeltilmeden önce) | `docs/adr/0003-at-rest-sifreleme-boslugu.md` |
| Tehdit modeli + rezidüel risk listesi | `docs/THREAT_MODEL.md` |
| Kullanım şartlarında dürüst güvenlik beyanı | `TERMS_OF_USE.md` §3 |
| Üç-kademe orkestrasyon ve kimin ne yazacağı | `docs/adr/0001-uc-kademe-orkestrasyon.md`, `docs/UI_UX_STANDARD.md` §4 |
| Lisans kararı: AGPL-3.0 | `LICENSE` |

---

## 4. Müfredat

On iki modül. Süreler **yönlendirici**dir, ölçülmüş değildir (bkz. §10). Her modül:
ön koşul → çıktı → konu → laboratuvar → değerlendirme.

---

### M0 · Yönelim ve ev kuralları — 2 saat
- **Ön koşul:** yok. **Kategoriler:** K10.
- **Çıktılar:** Ç1.5, Ç4.2.
- **Konular:** projenin tezi; `KURALLAR.md` maddeleri; "mühür = ölçüm"; yasaklı iddia
  sözcükleri; belge sürüm/onay akışı.
- **LAB-00 (belge denetimi):** Kursiyer `SECURITY_TESTS_TR.md` ve `README.md` dosyalarını
  `docs/UI_UX_STANDARD.md` §2.6'daki dürüstlük kuralına karşı denetler. Önce sözcük
  eşlemesiyle **aday** çıkarır ("%100", "garanti", "imkânsız", "sıfır risk"), sonra her adayı
  **cümle bağlamında** olumlama/olumsuzlama diye sınıflar — ihlal sayılan yalnız olumlamadır.
- **Değerlendirme:** Her aday için üçünden biri gerekçesiyle yazılı: (a) olumsuzlama → ihlal
  değil, (b) olumlama + ölçüm referansı var → ihlal değil, (c) olumlama + dayanak yok → ihlal,
  ölçüye dayalı yeniden yazım önerilir. **"Sıfır ihlal" geçerli bir sonuçtur**; ihlal sayısı
  puan değildir. *Bu iki dosyanın ölçülmüş sonucu §10.6'dadır — sözcük eşlemesi burada altı
  yanlış-pozitif verir.*

---

### M1 · Yerel-öncelikli mimari ve veri egemenliği — 4 saat
- **Ön koşul:** M0. **Kategoriler:** K1.
- **Çıktılar:** Ç1.1, Ç1.2.
- **Konular:** beş bileşen ve üç değişmez; koşullu-entropi saklama; üç hafıza kademesi;
  TTL vs `forget()`; loopback duruşu; MVP kapsam disiplini (eylem katmanının ~%90 riski
  taşıdığı gerekçesi — rakam `docs/PROJECT_BRIEF.md` Abstract'ta; §8 aynı gerekçeyi
  sayısız, "riskin ezici çoğunluğu" biçiminde tekrarlar).
- **LAB-01:** `run.py export --output test.kasa --verify` ile şifreli ihraç üret; yanlış
  parolayla doğrulamanın reddini göster. Sonra `forget(topic)` çağır ve üç yerde etkisini
  ölç: profil satırı, olay satırı, audit tombstone kaydı.
- **Değerlendirme:** Kursiyer, `forget()` ile `prune_expired_events()` arasındaki farkı
  **kod referansıyla** açıklar (`src/mcp_server/tools.py:158` vs `:287`) ve hangisinin
  köken zincirini koruduğunu söyler.

---

### M2 · Kriptografi uygulaması — 6 saat
- **Ön koşul:** M1. **Kategoriler:** K2.
- **Çıktılar:** Ç2.1.
- **Konular:** AES-GCM ve kimliği doğrulanmış şifreleme; nonce disiplini; AAD'nin rolü;
  DPAPI ve anahtar sahipliği; KDF seçimi (scrypt vs PBKDF2); encrypt-then-hash sırası;
  migrasyon güvenliği; "şifrelemeden önce sorguyu listele" ilkesi.
- **LAB-02a (AAD):** Bir profil hücresini bir olay hücresiyle takas et; `decrypt_cell`'in
  `InvalidTag` fırlattığını gözle (`src/vault/cell_crypt.py:56`). Sonra AAD'yi sabit bir
  dizeye çevir ve takasın **sessizce başarılı** olduğunu gör. İki davranışı yan yana yaz.
- **LAB-02b (erişim deseni):** `forget()`'in içerik kolonuna dokunan tüm SQL yollarını
  listele; kolon şifrelenince hangi sorgunun kırıldığını ve nasıl "decrypt-scan"e
  dönüştürüldüğünü izle (`docs/THREAT_MODEL.md` §L2).
- **Değerlendirme:** Kursiyer, "kasa.db şifreli bir dosya değil, ama içerik kolonları
  şifreli" ifadesini **çelişkisiz** biçimde açıklar ve hangi düşman sınıfına karşı ne
  koruduğunu `docs/THREAT_MODEL.md` düşman A–D tablosuyla eşler.

---

### M3 · Mahremiyet mühendisliği: maskeleme ve entropi — 5 saat
- **Ön koşul:** M2. **Kategoriler:** K8.
- **Çıktılar:** Ç3.2, Ç3.3.
- **Konular:** Shannon entropisi; eşik seçiminin FP/FN takası; yapısal önek kalkanı;
  bağlam koşullu hex; URL cerrahi taraması; maskele-vs-reddet; read-through-redact sınırı.
- **LAB-03a (kalibrasyon):** 30 zararsız + 20 gerçek-biçimli sahte sır içeren kendi
  korpusunu yaz. `redact.redact_text` ile tara; FP/FN say. `BASE64_MIN_ENTROPY`'yi 4.0'dan
  3.5'e indir, yeniden ölç: dosya yollarının maskelendiğini (kendine-DoS) gör
  (`src/vault/redact.py:26`).
- **LAB-03b (metadata):** Kendi test vault'unda, **şifreli kolonlara hiç dokunmadan**,
  yalnız `profile.key`, `events.source/type/timestamp` ve `audit.action` kolonlarından bir
  davranış profili çıkar. `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §1'deki bulguyu
  bağımsız olarak tekrar üret.
- **Değerlendirme:** FP/FN tablosu + eşik önerisi, **gerekçesiyle**. Metadata çıkarımı en az
  üç bağımsız çıkarım içerir ve her biri hangi kolondan geldiğini söyler.

---

### M4 · Yetkilendirme ve izin aracılığı — 6 saat
- **Ön koşul:** M1. **Kategoriler:** K4.
- **Çıktılar:** Ç2.2, Ç3.1.
- **Konular:** deny-by-default; kapsam sözdizimi ve wildcard; ad-uzayı kapısı vs içerik
  kapısı; rezerve kimlikler; ağdan çağrılamayan araçlar; argüman tip/aralık kapısı;
  bütçe sabitleri; MCP adaptörünün sunucuyu değiştirmeden nasıl takıldığı.
- **LAB-04a (canlı saldırı):** `py -3.14 _orch/redteam/live_mcp_attack.py` çalıştır. 25
  saldırının her birinin **red nedenini HTTP koduna göre sınıflandır**: 401 (kimlik yok),
  403 (kapsam yok), 404 (ad-uzayı dışı), 429 (debi), 422/400 (şema). Aynı kodun farklı
  anlamlarını ayır: `grant_permission` neden 404 alıyor, 403 değil?
- **LAB-04b (kapı fuzz'u):** `gate.validate_call`'a şu argümanları ver: `True` (bool),
  `"20"` (str), `0`, `101`, bilinmeyen anahtar, eksik zorunlu. Altı red mesajını üret ve
  her birini `src/agent/gate.py` satırına bağla.
- **LAB-04c (F-IMP):** İzole sunucuda `agent_id="browser"` ile `event_ingest` çağır; 200
  aldığını gözle. Sonra `RESERVED_AGENT_IDS`'e `"browser"` ekleyip tekrar dene. Bu düzeltmenin
  **neden kök çözüm olmadığını** yaz (ipucu: bir sonraki ayrıcalıklı ad).
- **Değerlendirme:** 25 saldırının sınıflandırma tablosu + LAB-04c'de "ad kara-listesi ≠
  kimlik doğrulama" sonucuna gerekçeli varış.

---

### M5 · Ajan güvenliği ve prompt injection — 6 saat
- **Ön koşul:** M4. **Kategoriler:** K3.
- **Çıktılar:** Ç1.3, Ç2.4.
- **Konular:** doğrudan vs dolaylı enjeksiyon; veri/talimat ayrımının yapısal uygulanışı;
  delimiter breakout; ad-uzayı allow-list + içerik denylist; provenance QC; harness'ın
  besleme-öncesi temizliği; "ele geçirilmiş model tavanı" düşüncesi.
- **LAB-05a:** `sanitize_untrusted_text`'i devre dışı bırak; `<<<END_UNTRUSTED_EVENT_DATA>>>`
  içeren bir olay üret ve damıtma prompt'unun yapısının bozulduğunu gözle. Geri aç, ZWSP
  eklemesinin bloğu koruduğunu gör (`src/vault/redact.py:190`).
- **LAB-05b:** `user.security.backdoor` gibi izinsiz ad-uzayına yazmaya çalışan bir
  enjeksiyon fact'i üret; QC kapısının reddettiğini `src/distill/engine.py:211`'de izle.
  Sonra `user.preferences.` önekiyle **aynı** zararlı içeriği dene: içerik kapısının
  (`CREDENTIAL_DENY`) devreye girdiğini gör. İki kapının neden ayrı olduğunu yaz.
- **LAB-05c:** `tools/model_bench` A1 probunu tek bir modele karşı **iki kez** koş. Sonuç
  değişirse ne yapılmalı? (Cevap `docs/MODEL_SECIMI_TR.md` §5'te.)
- **Değerlendirme:** Kursiyer, KASA'nın enjeksiyona karşı savunmasının **yapısal** olduğunu
  ve "model dirençli" iddiasından farkını, `docs/MODEL_BENCH_hermes3-8b.md` "Dürüst sınırlar"
  bölümüne atıfla açıklar.

---

### M6 · Denetlenebilirlik ve atıf — 5 saat
- **Ön koşul:** M2. **Kategoriler:** K5.
- **Çıktılar:** Ç1.4, Ç2.3.
- **Konular:** hash zinciri mekaniği; tahrif tespitinin sınırı; checkpoint mühürü ve
  arşiv; sahte tohum reddi; rotasyon ile zincirin etkileşimi; sessiz ret sorunu; tombstone.
- **LAB-06a:** Zinciri doğrula (`verify_chain` → True); şifreli bir `details` hücresinde tek
  karakter değiştir; tekrar doğrula (→ False). Sonra bir satır **sil** ve tespiti gözle.
- **LAB-06b:** `create_checkpoint()` → `archive_up_to()` → `verify_chain()` sırasını koş.
  Ardından mühürsüz bir satırı silmeyi dene ve reddi gözle. Son olarak
  *checkpoint → rotate → arşiv* sırasını dene ve `docs/FLOW_CONTROL_TR.md` DEBI-2'deki "yan
  bulgu"nun neden ortaya çıktığını açıkla.
- **LAB-06c (atıf):** `_orch/redteam/persistent_attacker.py` çalıştır; saldırganın kendi
  günlüğü ile savunucunun audit kaydını uzlaştır. Fark = **görünmezlik**. Kaç deneme
  kaydedilmedi?
- **Değerlendirme:** Kursiyer "zincir neyi kanıtlar, neyi kanıtlamaz" sorusuna iki maddeyle
  cevap verir ve tamper-evident/tamper-proof ayrımını doğru kullanır.

---

### M7 · Debi ve kaynak kontrolü — 3 saat
- **Ön koşul:** M4, M6. **Kategoriler:** K9.
- **Çıktılar:** Ç3.4.
- **Konular:** token-bucket; sınırlayıcının izin kontrolünden önce gelmesinin gerekçesi
  (reddedilen çağrı bile audit yazar); kova tahliyesi; anahtarlı dedup; sayaç sinyali.
- **LAB-07:** İzole sunucuya **sabit** `agent_id` ile 150 istek at; 429 sayısını kaydet.
  Aynı testi **dönen** `agent_id` ile tekrarla; 429 sayısını kaydet. Sonra kova sözlüğü
  boyutunu ölç (3000 kimlik). `max_buckets` tahliyesinin etkisini ölç
  (`src/mcp_server/ratelimit.py:30`).
- **Değerlendirme:** Kursiyer iki ölçümü tablolar ve **kök nedeni** ("kimlik
  doğrulanmıyor") semptomdan ("fren tutmuyor") ayırır.

---

### M8 · Yerel model operasyonu ve model seçimi — 6 saat
- **Ön koşul:** M5. **Kategoriler:** K7.
- **Çıktılar:** Ç2.5, Ç4.5.
- **Konular:** tezgahın üretim kodunu kullanması; altı prob ailesi; deterministik notlama
  ve `heuristic` işaretlemesi; şema kısıtlı çıktı; Modelfile paketleme; konfigürasyonun tek
  yetkili kaynağı; ölçek ≠ dayanıklılık bulgusu.
- **LAB-08a:** `py -3.14 -m tools.model_bench --model <model>` ile kurulu iki modeli ölç;
  `docs/MODEL_BENCH_*.md` damgalarını üret ve karşılaştır.
- **LAB-08b:** Damıtma çağrısını üç modda koş: kısıtsız, `format:"json"`, şema kısıtlı.
  Üçünün de çıktısını kaydet. `docs/MODEL_SECIMI_TR.md` Bulgu 4'ü bağımsız doğrula ya da
  **çürüt** (çürütmek de geçerli bir sonuçtur; damgala).
- **LAB-08c (kabul kuralı):** Bir kabul kuralı yaz: "hangi metrik hangi eşikte düşerse
  değişiklik reddedilir". `docs/MODEL_SECIMI_TR.md` §6'daki kuralın neden bu biçimde
  yazıldığını (itaat ↔ enjeksiyon aynı davranışın iki yüzü) açıkla.
- **Değerlendirme:** İki model damgası + LAB-08c'de yazılan kabul kuralı, ölçülebilir bir
  eşik ve reddetme koşulu içeriyor.

---

### M9 · Ölçüm bütünlüğü — 8 saat *(programın çekirdeği)*
- **Ön koşul:** M2, M4, M6 (en az ikisi). **Kategoriler:** K6.
- **Çıktılar:** Ç1.5, Ç4.1, Ç4.2.
- **Konular:** dedektörün iki arıza modu; yanlış-PASS ve yanlış-FAIL avı; pozitif kontrol
  ve alet negatif-kontrolü; üçüncü durum (`ERROR`) ve `DOĞRULANMADI` verdict'i; kapsam
  beyanı; drift; beklenti etiketi; ölçen ≠ düzelten; sahte kırmızının insan maliyeti;
  alan taraması (yangın alarmı, havacılık, muhasebe denetimi — §7.2).
- **LAB-09a (yanlış-PASS):** `MB-JSON-YIELD` ölçütünü geçici olarak kaldır ve küçük bir
  modeli koş; boş dizinin PASS sayıldığını gör. Ölçütü geri koy. İki koşuyu yan yana yaz
  (`docs/MODEL_SECIMI_TR.md` §1.1'in bağımsız tekrarı).
- **LAB-09b (pozitif kontrol):** Tarama kapsamına, tarayıcının **bulmak zorunda olduğu**
  bilinen bir işaret yerleştir (EICAR/GTUBE mantığı). Tarayıcı bulamazsa bulgu yok demek
  değildir — **alet bozuk** demektir. `tools/security_bench/checks/scan.py` kapsamına karşı
  koş.
- **LAB-09c (üçüncü durum):** `tools/security_bench` çıktısında `ERROR` ve `FAIL`
  kalemlerini ayır; verdict hesabında `ERROR`'un yayın engeli **üretmediğini**
  `tools/security_bench/report.py:38`'de doğrula. Bunun neden doğru olduğunu (ve ne zaman
  yanlış olacağını) tartış.
- **LAB-09d (drift):** `tools/drift_canary.py --update` ile temel çizgi al; `kasa.toml`'da
  bir ayar değiştir; canary'nin drift'i yakaladığını gör.
- **LAB-09e (negatif kontrol):** `src/dashboard/stats.py`'ye ham (deşifre edilmiş) bir hücreyi
  yanıta sızdıran bir satır ekle; `tests/test_dashboard_stats.py`'nin bunu yakalayıp
  yakalamadığını ölç. Yakalamazsa, yakalayan testi **sen yaz**. (Değişikliği geri al.)
- **Değerlendirme:** Beş laboratuvarın dördü tamamlanmış; LAB-09e'de ya mevcut testin
  yakaladığı ölçümle gösterilmiş ya da yeni test yazılmış. Kursiyer, "boş çıktı = 0 bulgu"
  varsayımının neden bir **istatistik hatası** olduğunu açıklar (§7.2).

---

### M10 · Yönetişim, karar kaydı ve lisans — 3 saat
- **Ön koşul:** M0. **Kategoriler:** K10.
- **Çıktılar:** Ç4.3, Ç4.4.
- **Konular:** ADR anatomisi; kırık vaadi düzeltmeden önce raporlama disiplini
  (`docs/adr/0003`); tehdit modeli ve rezidüel risk yazımı; onay/sürüm akışı; AGPL-3.0 ve
  ikili lisans mantığı; kullanım şartlarında dürüst beyan.
- **LAB-10a:** `docs/adr/` biçiminde kendi ADR'ni yaz: bir mimari karar, reddettiğin
  alternatif ve **reddin bedeli**.
- **LAB-10b:** Kendi projen için `docs/THREAT_MODEL.md` biçiminde bir tehdit modeli üret:
  düşman sınıfları, savunmalar ve en az üç **rezidüel risk** — gizlemeden.
- **Değerlendirme:** ADR üç bölümü de içeriyor (sebep/karar/sonuç) ve en az bir rezidüel
  risk **açıkça kabul edilmiş** olarak yazılmış.

---

### M11 · Sentez projesi — 8–16 saat
- **Ön koşul:** M1–M9. **Kategoriler:** tümü.
- **Çıktılar:** Ç2.*, Ç3.*, Ç4.*.
- **Görev (üç seçenekten biri):**
  1. **Yeni bir araç ekle.** MCP yüzeyine salt-okunur bir araç ekle: kapsam tanımı, gate
     kuralı, audit kaydı, izin seed'i **olmadan** deny-by-default davranışın kanıtı, ve
     `_orch/redteam/live_mcp_attack.py`'a bu aracı hedefleyen bir saldırı adımı.
  2. **Bir boşluğu kapat ve kanıtla.** P1 kimlik bağlamanın bir parçasını uygula
     (`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §8/P1) ve **kabul kapısını** koş:
     dönen `agent_id` ile 300 istek → 429 devreye giriyor mu?
  3. **Bir ölçüm aletini onar.** Mevcut bir kontrolün yanlış-PASS veya yanlış-FAIL
     üretebildiğini göster, düzelt, ve düzelttiğini **aletin kendisiyle** kanıtla.
- **Değerlendirme (rubrik, 100 puan):** ölçüm kanıtı 40 · dürüst sınır beyanı 20 ·
  kod/test kalitesi 20 · belge (sebep/karar/sonuç) 20. **Sert kural:** ölçüm referansı
  olmayan mutlak iddia içeren teslim, diğer puanlardan bağımsız olarak **reddedilir**
  (`docs/UI_UX_STANDARD.md` §2.6 ile tutarlı).

---

## 5. Öğrenme patikaları

### Patika A — Temel · 2 gün (~13 saat)
**Kime:** karar vericiler, ürün/güvenlik ilgilileri, meraklı geliştiriciler.

| Gün | Modüller | Saat |
|---|---|---|
| 1 | M0 (2) + M1 (4) + M4 kısmi: LAB-04a (2) | 8 |
| 2 | M6 kısmi: LAB-06a (2) + M9 kısmi: LAB-09c (2) + kapanış tartışması (1) | 5 |

**Bitiş yeterliliği:** Ç1.1, Ç1.2, Ç1.4, Ç1.5. Kursiyer bir ajan mimarisine bakıp güvenlik
sınırının nerede olduğunu ve denetim iddiasının neyi kapsadığını söyleyebilir.

### Patika B — Uygulayıcı · 5 gün (~37 saat)
**Kime:** yerel-öncelikli veya ajan sistemi kuran geliştiriciler.

| Gün | Modüller | Saat |
|---|---|---|
| 1 | M0 (2) + M1 (4) + M2 başlangıç (2) | 8 |
| 2 | M2 tamam (4) + M3 (5 → 4 sıkıştırılmış) | 8 |
| 3 | M4 (6) + M7 (2, LAB-07) | 8 |
| 4 | M5 (6) + M6 kısmi (2) | 8 |
| 5 | M9 (LAB-09a/b/c) (5) | 5 |

**Bitiş yeterliliği:** Ç2.1, Ç2.2, Ç2.4 · Ç3.1, Ç3.2, Ç3.3, Ç3.4 · Ç4.1.
**Kapsam dışı (dürüst not):** Ç2.3 yalnız **kısmi** işlenir (M6 kısmi: LAB-06a; checkpoint/arşiv
kısmı olan LAB-06b bu patikada yok) ve **Ç2.5 hiç işlenmez** — çıktısı M8'dedir, M8 bu patikada
yoktur. Ç2.5 gereken kursiyer M8'i eklemeli (+6 saat) ya da Patika C'ye geçmelidir.

### Patika C — İleri / araştırma · 10 gün (~70 saat)
**Kime:** güvenlik araştırmacıları, lisansüstü seminer katılımcıları, denetçiler.

| Gün | Modüller |
|---|---|
| 1 | M0, M1 |
| 2 | M2 |
| 3 | M3 |
| 4 | M4 |
| 5 | M5 |
| 6 | M6, M7 |
| 7 | M8 |
| 8 | M9 (tam, beş laboratuvar) |
| 9 | M10 + M11 başlangıç |
| 10 | M11 teslim + akran değerlendirmesi |

**Bitiş yeterliliği:** Ç1–Ç4 tamamı. **Ek beklenti (araştırma katkısı):** kursiyerin
sentez projesi, KASA'nın açık listesindeki bir maddeyi ya kapatmalı ya da **ölçümle
çürütmelidir** — mevcut belgede yazan bir iddiayı yanlışlamak, tam puanlı bir sonuçtur.

---

## 6. Değerlendirme ve ölçme

**İlke:** Programın kendi ölçme aracı da K6'ya tabidir. "Kursiyer öğrendi" iddiası, ölçüm
referansı olmadan yazılmaz.

| Araç | Ne ölçer | Yanlış-PASS riski | Karşı-önlem |
|---|---|---|---|
| Laboratuvar çıktısı (artefakt) | uygulama becerisi | kopyala-yapıştır | artefakt kursiyerin **kendi** korpusunu/ölçümünü içermeli (LAB-03a, LAB-09a) |
| Sınıflandırma tablosu (LAB-04a) | kavrayış | ezber | red kodları koşuya göre değişir; gerekçe istenir |
| Kabul kuralı yazımı (LAB-08c) | tasarım | genel-geçer cümle | ölçülebilir eşik + reddetme koşulu zorunlu |
| Sentez projesi (M11) | bütünleşik | abartılı iddia | mutlak iddia → doğrudan ret |
| Akran değerlendirmesi (Patika C) | eleştiri becerisi | nezaket enflasyonu | değerlendirici en az bir **ölçülebilir** itiraz yazmak zorunda |

**Programın kendi negatif kontrolü:** Her dönem, laboratuvarlardan birine **bilerek bozuk**
bir varyant konur (ör. eşiği kaydırılmış redact, sahte tohumlu zincir). Kursiyerlerin
hiçbiri bozukluğu yakalamıyorsa, sorun kursiyerlerde değil **ölçme aracındadır** —
laboratuvar yeniden tasarlanır.

---

## 7. Atıflar

> **Ayrım kritik.** §7.1 bu depodaki **gerçek dosyalardır**; her yol yazılmadan önce
> varlığı kontrol edildi. §7.2 **dış kaynaklardır**; künyesinden (yazar/yıl/başlık) emin
> olunmayanlar `[DOĞRULANMALI]` etiketiyle işaretlenmiştir. Bu belgede sahte DOI, sahte
> sayfa numarası veya uydurma yazar adı **yoktur**; emin olunmayan yerde etiket vardır.

### 7.1 İç atıflar (bu depo)

**Kural belgeleri ve yönetişim**
`KURALLAR.md` · `LICENSE` (AGPL-3.0) · `TERMS_OF_USE.md` · `docs/UI_UX_STANDARD.md` ·
`docs/adr/0001-uc-kademe-orkestrasyon.md` · `docs/adr/0002-guvenlik-benchmark-kanit.md` ·
`docs/adr/0003-at-rest-sifreleme-boslugu.md`

**Mimari ve tehdit**
`README.md` · `README.tr.md` · `docs/PROJECT_BRIEF.md` · `docs/THREAT_MODEL.md` ·
`docs/AGENT_BRIDGE.md` · `docs/FLOW_CONTROL_TR.md` · `docs/FLOW_CONTROL_EN.md` ·
`docs/BEKCI_KURALLARI.md` · `docs/GUVENLIK_CIKIS_PLANI.md` · `docs/INGEST_LABELING_PLAN_TR.md`

**Ölçüm damgaları ve denetim**
`docs/SECURITY_BENCHMARK.md` · `docs/security_bench_result.json` ·
`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` · `docs/KASA_SAGLIK_2026-08-01.md` ·
`docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md` · `docs/OLCUM_BUTUNLUGU_VIZYON_2026-08-02.md` ·
`docs/MODEL_SECIMI_TR.md` · `docs/MODEL_BENCH_hermes3-8b.md` · `docs/MODEL_BENCH_kasa-agent-8b.md` ·
`docs/MODEL_BENCH_qwen2.5-7b.md` · `docs/MODEL_BENCH_qwen2.5-3b.md` ·
`docs/SECRET_SCAN_CORPUS.md` · `docs/drift_baseline.json` · `SECURITY_TESTS_TR.md` ·
`SECURITY_TESTS_EN.md` · `docs/TRAINING_PLAN_15D.md`

**Kaynak kodu (satır referanslı)**

| Referans | İçerik |
|---|---|
| `src/agent/gate.py:25`–`:34` | bütçe sabitleri |
| `src/agent/gate.py:44` | araç kayıt defteri (üç salt-okunur + kapalı yazıcı) |
| `src/agent/gate.py:75` | içerik kapısı (kredensiyel denylist) |
| `src/agent/gate.py:85` | `validate_call` — deterministik argüman kapısı |
| `src/agent/harness.py` | sınırlı araç-çağrısı döngüsü, güvenlik sınırı docstring'i |
| `src/agent/store.py` | `resolve_model` — tek yetkili model çözücü |
| `src/vault/redact.py:19`, `:26`, `:49` | entropi eşiği, base64 tabanı, yapısal önekler |
| `src/vault/redact.py:63`, `:84`, `:146`, `:169`, `:190` | entropi, maskeleme, URL, `scan`, delimiter |
| `src/vault/cell_crypt.py:33`, `:46`, `:56`, `:67`–`:76` | anahtar, şifrele/çöz, AAD kurucuları |
| `src/vault/audit.py:28`, `:46`, `:95`, `:143`, `:166` | son hash, kayıt, doğrulama, checkpoint, arşiv |
| `src/vault/database.py:46`, `:84`, `:178`, `:191` | anahtar üretimi, rotasyon, bağlantı, `secure_delete` |
| `src/vault/schema.py` | tablo DDL'leri (events/profile/audit/permissions) |
| `src/export/encrypt.py:27` | scrypt KDF |
| `src/mcp_server/server.py:63`, `:64`, `:70`, `:81`–`:84`, `:152`, `:162` | rezerve kimlik, `PUBLIC_TOOLS`, sınırlayıcı, `browser` oto-izni, 429, ad-uzayı |
| `src/mcp_server/tools.py:39`, `:158`, `:221`, `:287`, `:344`, `:386` | izin kontrolü, `forget`, `audit_read`, `prune`, `event_ingest`, HMAC dedup |
| `src/mcp_server/ratelimit.py:20`, `:30`, `:43` | token-bucket, tahliye, `allow` |
| `src/distill/engine.py:29`, `:42`, `:48`, `:79`, `:211`, `:224` | ad-uzayı allow-list, provenance tavanı, şema, UNTRUSTED marker, QC |
| `src/dashboard/stats.py` | read-through-redact aggregator |
| `src/mcp_adapter/proxy.py`, `src/mcp_adapter/__main__.py` | MCP adaptörü (SDK'siz çekirdek + FastMCP yüzeyi) |

**Ölçüm ve saldırı araçları**
`tools/security_bench/run.py` · `tools/security_bench/report.py` ·
`tools/security_bench/checks/authz.py` · `tools/security_bench/checks/crypto.py` ·
`tools/security_bench/checks/audit.py` · `tools/security_bench/checks/scan.py` ·
`tools/security_bench/checks/fuzz.py` · `tools/security_bench/b1_seal.py` ·
`tools/model_bench/run.py` · `tools/model_bench/probes.py` ·
`tools/model_bench/report.py` · `tools/drift_canary.py` ·
`tools/grant_agent_scope.py` · `tools/migrate_l2_encrypt.py` ·
`_orch/redteam/live_mcp_attack.py` · `_orch/redteam/persistent_attacker.py` ·
`_orch/redteam/named_pipe_identity_spike.py` · `_orch/redteam/attack_catalog.json` ·
`_orch/redteam/attacker_journal.jsonl` · `_orch/redteam/live_attack_log.jsonl` ·
`_orch/redteam/model_redteam_results.json` · `_orch/loop/selftest_rollback.py` ·
`_orch/loop/guard.py` · `_orch/loop/board.json`

**Testler (laboratuvar dayanağı)**
`tests/test_l2_at_rest.py` · `tests/test_l2_migration.py` · `tests/test_authz.py` ·
`tests/test_agent_gate.py` · `tests/test_flow_control.py` · `tests/test_ratelimit_eviction.py` ·
`tests/test_distill_injection.py` · `tests/test_delimiter_breakout.py` ·
`tests/test_semantic_injection.py` · `tests/test_denylist_obfuscated.py` ·
`tests/test_dashboard_stats.py` · `tests/test_bench_error_status.py` ·
`tests/test_bench_coverage_verdict.py` · `tests/test_bench_scan_scope.py` ·
`tests/test_secret_scan_allowlist.py` · `tests/test_drift_canary.py` ·
`tests/test_mcp_adapter.py` · `tests/test_integration.py`

**Diğer**
`models/kasa-agent.Modelfile` · `design_system/tokens.css` · `dashboard_ui/app.js` ·
`browser_extension/` · `build_kasa.ps1` · `run.py` · `kasa.toml.example`

### 7.2 Dış atıflar (yerleşik kaynaklar)

**Mimari ve ilkeler**
- Kleppmann, M.; Wiggins, A.; van Hardenberg, P.; McGranaghan, M. — *"Local-first software:
  You own your data, in spite of the cloud"*, Ink & Switch, 2019.
- Saltzer, J. H.; Schroeder, M. D. — *"The Protection of Information in Computer Systems"*,
  Proceedings of the IEEE, 1975. (fail-safe defaults, least privilege)
- Kerckhoffs, A. — *"La cryptographie militaire"*, Journal des sciences militaires, 1883.
  (güvenlik anahtarda, algoritmanın gizliliğinde değil)
- **Model Context Protocol (MCP)** — Anthropic tarafından yayımlanan açık protokol
  spesifikasyonu (2024). Sürüm numaraları hızla değişir; güncel spesifikasyon kontrol
  edilmeli.
- STRIDE tehdit modelleme çerçevesi — Microsoft.

**Kriptografi**
- NIST SP 800-38D — *"Recommendation for Block Cipher Modes of Operation: Galois/Counter
  Mode (GCM) and GMAC"*, 2007. (AES-GCM, AAD semantiği)
- Shannon, C. E. — *"A Mathematical Theory of Communication"*, Bell System Technical
  Journal, 1948. (entropi)
- RFC 7914 — *"The scrypt Password-Based Key Derivation Function"*, 2016.
- RFC 8018 — PKCS #5 v2.1, *"Password-Based Cryptography Specification"*, 2017. (PBKDF2)
- Lamport, L. — *"Password Authentication with Insecure Communication"*, Communications of
  the ACM, 1981. (hash zinciri)
- S/KEY tek-kullanımlık parola sistemi — RFC 1760 `[DOĞRULANMALI]` (RFC numarası ve yılı
  doğrulanmalı; sistemin adı ve Lamport zinciriyle ilişkisi yerleşiktir).
- Windows Data Protection API (DPAPI) — `CryptProtectData` / `CryptUnprotectData`,
  Microsoft platform belgeleri.
- SQLCipher — Zetetic LLC; SQLite için tam dosya şifrelemesi.

**Yetkilendirme ve kimlik**
- RFC 6749 — *"The OAuth 2.0 Authorization Framework"*, 2012. (kapsam/scope modeli)
- RFC 9449 — *"OAuth 2.0 Demonstrating Proof of Possession (DPoP)"*, 2023. (taşıyıcı
  token'ın sahiplik kanıtına bağlanması — KASA'nın P1 kimlik bağlama adımıyla kavramsal
  akrabalık)

**Ajan güvenliği**
- **OWASP Top 10 for LLM Applications** — LLM01: Prompt Injection. Liste sürümlenir
  (2023 ve 2025 sürümleri mevcuttur); atıf yapılırken **sürüm belirtilmelidir**.
- "Prompt injection" teriminin yaygınlaşması — Simon Willison, 2022 `[DOĞRULANMALI]`
  (terimin ilk kullanımının atfı tartışmalıdır; blog yazısı tarihi doğrulanmalı).
- "Lethal trifecta" (özel veriye erişim + güvenilmez içeriğe maruziyet + dışarıyla
  iletişim) — Simon Willison `[DOĞRULANMALI]` (adlandırma ve yıl doğrulanmalı; desen
  `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §4.4'te aynen kullanılmıştır).
- Five Eyes / CISA ortak ajansal-AI rehberi (Mayıs 2026) `[DOĞRULANMALI]` — bu belgeye
  `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §6.2 üzerinden dolaylı atıf yapılmıştır;
  birincil kaynak doğrulanmadan alıntılanmamalıdır.

**Ölçüm bütünlüğü ve güvenilirlik**
- Avizienis, A.; Laprie, J.-C.; Randell, B.; Landwehr, C. — *"Basic Concepts and Taxonomy of
  Dependable and Secure Computing"*, IEEE Transactions on Dependable and Secure Computing,
  2004. (signaled/unsignaled failure; dedektörün kendi arıza modları)
- Altman, D. G.; Bland, J. M. — *"Absence of evidence is not evidence of absence"*, BMJ, 1995.
- Goodhart, C. — 1975. Yaygın "bir ölçü hedef hâline gelince iyi bir ölçü olmaktan çıkar"
  formülasyonu Marilyn Strathern'e (1997) atfedilir `[DOĞRULANMALI]`.
- NIST SP 800-90B — *"Recommendation for the Entropy Sources Used for Random Bit
  Generation"*, 2018. (yanlış-pozitif bütçesi kavramı)
- ISO 26262 — Yol araçları, fonksiyonel güvenlik; **Latent Fault Metric** (güvenlik
  mekanizmasının kendi gizli arızası için sayısal hedef).
- NFPA 72 (yangın alarmı: ALARM / SUPERVISORY / **TROUBLE**), ISA-18.2 (proses alarm
  durumları), IEC 60601-1-8 (fizyolojik ≠ **teknik** alarm), ARINC 429 (her veri
  kelimesinde geçerlilik biti) — "ölçemedim" için üçüncü durumun yerleşik örnekleri.
  Madde/bölüm numaraları için birincil standartlara bakılmalıdır.
- SARIF — Static Analysis Results Interchange Format, OASIS. `executionSuccessful` alanı
  ile bulgu-yokluğu / çalıştırılamama ayrımı. Sürüm 2.1.0 `[DOĞRULANMALI]`.
- SPDX — `NONE` ("baktım, yok") ≠ `NOASSERTION` ("iddia etmiyorum").
- Nagios eklenti sözleşmesi — çıkış kodu 3 = `UNKNOWN`, OK/WARNING/CRITICAL'dan ayrı.
- Muhasebe denetim görüşü taksonomisi: temiz / şartlı / olumsuz / **görüş bildirmekten
  kaçınma** (disclaimer of opinion) — "ölçemedim"in hukuken bağlayıcı karşılığı.
- EICAR anti-virüs test dosyası ve GTUBE spam test dizesi — **pozitif kontrol** deseninin
  yerleşik örnekleri.
- Kanonik vakalar (dedektör–gerçeklik kopması): Three Mile Island (1979), Air France 447
  (2009), Deepwater Horizon (2010). Ayrıntılar için resmî kaza raporlarına bakılmalıdır.

**Hukuk ve uyum**
- GDPR — Regulation (EU) 2016/679. Özellikle Md. 5(2) hesap verebilirlik, Md. 17 silme
  hakkı, Md. 32 işleme güvenliği.
- DORA — Regulation (EU) 2022/2554 (dijital operasyonel dayanıklılık).
- EU AI Act — Regulation (EU) 2024/1689. Yüksek-risk yükümlülüklerinin **yürürlük
  takvimi** `[DOĞRULANMALI]` (`docs/OLCUM_BUTUNLUGU_VIZYON_2026-08-02.md` §6'da aktarılan
  erteleme tarihleri birincil kaynaktan teyit edilmelidir).
- ISO/IEC 42001 — yapay zekâ yönetim sistemi standardı (2023).
- NIST SP 800-53 — AU-5, denetim kaydı süreci arızalarına yanıt.
- PCI DSS v4.0 — 10.7.2 (denetim mekanizması arızasının tespiti ve raporlanması)
  `[DOĞRULANMALI]` (madde numarası birincil standarttan teyit edilmeli).

**Eğitim tasarımı**
- Bloom, B. S. ve ark. — *Taxonomy of Educational Objectives*, 1956; gözden geçirilmiş
  sürüm: Anderson, L. W.; Krathwohl, D. R., 2001. (§2'deki fiil hiyerarşisinin dayanağı)

---

## 8. Yol haritası

**İlke (K6'dan devralınan):** önce ölçüm aleti, sonra ölçtüğü şey. Program materyali,
üzerine kurulduğu laboratuvarlar tekrar-üretilebilir olmadan yayımlanmaz.

| Aşama | Tarih | İş | Kabul ölçütü |
|---|---|---|---|
| **A0 — Onay** | 2026 Q3 (Ağustos) | Bu belgenin sahip tarafından onaylanması; sürüm ilanı | `KURALLAR.md` §2 uyarınca sürüm ilan edildi |
| **A1 — Laboratuvar sertleştirme** | 2026 Q3 (Eylül) | 26 laboratuvarın her biri temiz bir makinede sıfırdan koşturulur; adım adım komutlar yazılır | Her lab için "girdi → komut → beklenen çıktı" üçlüsü kayıtlı; en az bir lab **kasıtlı olarak bozulup** yakalanabildiği gösterilmiş |
| **A2 — Pilot 1 (iç)** | 2026 Q4 (Ekim) | Patika A, 2–4 kişilik iç grup | Kursiyerlerin ≥%75'i Ç1.5'i (ERROR ≠ FAIL) bağımsız olarak açıklıyor |
| **A3 — Materyal üretimi** | 2026 Q4 (Kasım–Aralık) | Slayt yerine **çalıştırılabilir** materyal: her modül için bir `README` + kabul betiği; `docs/` altında sürümlenir | Materyal kopyalanan bir makinede dış ağ olmadan koşuyor (air-gap uyumu) |
| **A4 — Pilot 2 (dış)** | 2027 Q1 | Patika B, dış katılımcılarla; geri bildirim tarihli olarak kaydedilir | Her modül için en az bir "bu lab çalışmadı" kaydı ve nedeni yazılı |
| **A5 — Ölçme-değerlendirme kalibrasyonu** | 2027 Q1–Q2 | §6'daki negatif kontrol uygulanır: bozuk varyantı kimse yakalamıyorsa lab yeniden tasarlanır | Kalibrasyon raporu tarihli olarak `docs/` altında |
| **A6 — Patika C ve araştırma katkısı** | 2027 Q2–Q3 | İleri patika açılır; sentez projelerinden çıkan bulgular depoya geri işlenir | En az bir kursiyer bulgusu ADR'ye veya tehdit modeline girmiş |
| **A7 — Sürdürülebilirlik kararı** | 2027 Q3 | §9'daki modelin gözden geçirilmesi | Karar ADR olarak kaydedilmiş |

**Bağımlılık uyarısı (dürüst):** A1'in kapsamı, KASA'nın kendi açık listesindeki maddelerden
bağımsız **değildir**. Özellikle M11-seçenek-2 (P1 kimlik bağlama) laboratuvarı, o iş
yapılmadan yalnızca "boşluğu göster" biçiminde koşabilir; "boşluğu kapat ve kanıtla"
biçimi P1'in uygulanmasına bağlıdır.

---

## 9. Sürdürülebilirlik ve lisans

**Materyal lisansı:** Program materyali KASA ile aynı lisansa tabidir — **AGPL-3.0**
(`LICENSE`). Bireysel, eğitim ve araştırma kullanımı serbesttir; materyal kopyalanabilir,
değiştirilebilir ve dağıtılabilir; türev çalışmalar aynı lisansla açılır.

**Ticari eğitim seçeneği:** Türevini açmak istemeyen kurumlar için ayrı **ticari lisans**
yolu tanımlıdır (sahibin kararı). Ticari seçeneğin programa yansıması şunlardır: kurum-içi
kapalı türev materyal üretimi, özel oturum, ve kurumun kendi kod tabanına uyarlanmış
laboratuvar. Bu, açık materyalin kapsamını **daraltmaz** — açık sürüm her zaman tam
patikaları içerir.

**Neden bu model:** Eğitim materyali, üzerinde çalıştığı yazılımdan daha kısıtlayıcı bir
lisansla dağıtılırsa, "veri ve bilgi sahipliği" tezi kendi içinde çelişir. AGPL + ticari
ikili lisans, bireysel kullanıcının hakkını korurken sürdürülebilirliği kuruma yükler.
(Referans model olarak Plausible Analytics'in AGPL-3.0 + barındırılan ticari hizmet
düzeni gösterilebilir; sahibin kararında anılan diğer örneklerin güncel lisans durumu
`[DOĞRULANMALI]`.)

**Katkı ve atıf:** Kursiyer katkıları (yeni laboratuvar, düzeltilmiş ölçüt, çürütülmüş
iddia) depoya alınırken katkı sahibinin adı kayıtta kalır. Projenin sahiplik atfı
(`Erhan`) korunur.

---

## 10. Dürüst sınırlar

Bu bölüm programın **satmadığı** şeyleri sayar. Kurallar gereği bu bölüm kısaltılamaz.

**10.1 Bu bir sertifika programı değildir.** Akredite bir kurumun sınavı, tanınmış bir
yeterlilik belgesi veya mesleki bir unvan üretmez. §6'daki değerlendirme araçları
**öğrenmeyi ölçmek** için tasarlanmıştır, üçüncü taraflara yeterlilik beyan etmek için
değil.

**10.2 Süreler ölçülmemiştir.** §4'teki saatler tasarım tahminidir; hiçbir pilot henüz
koşmamıştır (bkz. §8/A2). İlk pilottan sonra bu tablo **ölçülmüş değerlerle**
güncellenmelidir. Şu anki hâliyle bu bir tahmindir ve öyle işaretlenmiştir.

**10.3 KASA mühürlü değildir; program bunu gizlemez.** Ölçülmüş, açık kalemler:
- **F-IMP / kimlik bağlama (E2):** `agent_id` istemci-beyanlıdır; `browser` kimliği taklit
  edilerek `events:write` izni devralınabildi (izole ölçüm, HTTP 200 —
  `docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md` §2). Kök çözüm (P1) **uygulanmadı**;
  bir fizibilite spike'ı yapıldı (`_orch/redteam/named_pipe_identity_spike.py`).
- **At-rest boşluğu ve metadata deseni (E4):** İçerik kolonları şifrelidir
  (`CRYPTO-ATREST` PASS, `docs/SECURITY_BENCHMARK.md`), ama `kasa.db` şifreli bir dosya
  değildir ve düz metin metadata'dan davranış profili çıkarılabilmektedir (ölçüldü —
  `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §1). Tam-DB şifreleme kararı açıktır
  (`docs/adr/0003`).
- **Egress ölçülmemiştir (E3):** `docs/GUVENLIK_CIKIS_PLANI.md` Faz 1–4 planlıdır,
  **hiçbiri kurulmamıştır**. Dolayısıyla program "veri dışarı çıkmaz" iddiasını
  **öğretmez**; öğrettiği şey, bu iddianın hangi ölçümle kurulabileceğidir.
- **Aktif tarama bulgusu:** Son damgada `SCAN-SECRETS` **FAIL (critical)** durumundadır
  (16 denetlenmemiş bulgu) ve `SCAN-BANDIT` Medium bulguları triyaj edilmemiştir
  (`docs/SECURITY_BENCHMARK.md`, 2026-08-02).

**10.4 Program bunları öğretmez:**
- Ağ MITM savunması, fiziksel erişim savunması, donanım güven kökü (TPM/Secure Boot).
- Kriptografik **primitif tasarımı**. Program primitif *uygulamasını* öğretir; yeni şifre
  tasarlamak kapsam dışıdır ve caydırılır.
- Çok-kullanıcılı/kurumsal kimlik yönetimi (SSO, dizin servisleri), ölçekli SIEM.
- İnce ayar (fine-tuning) mühendisliğinin kendisi — yalnız **kabul kuralı** tarafı işlenir
  (`docs/MODEL_SECIMI_TR.md` §6).
- Eylem katmanı (A1–A3): form doldurma, işlem gönderme, ödeme. Bunlar KASA'da bilinçli
  olarak ertelenmiştir (`docs/PROJECT_BRIEF.md` §8) ve program da ertelemeyi izler.
- Windows dışı platformlar. DPAPI Windows'a özgüdür (`docs/THREAT_MODEL.md`); macOS/Linux
  için KeyProvider dikişi tasarlanmıştır ama **yazılmamıştır**.

**10.5 Kapatılamayan sınırlar (rezidüel, gizlenmiyor).** Aynı kullanıcı bağlamında çalışan
kötü yazılım DPAPI'yi çağırabilir; bellekteki düz metin swap/hibernate ile pagefile'a
düşebilir. İkisinin de Python'da pratik mitigasyonu yoktur
(`docs/THREAT_MODEL.md`, `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §4.5). Program
bunları **çözmez**; doğru şekilde **beyan etmeyi** öğretir.

**10.6 LAB-00'ın ölçülmüş sonucu: hedef dosyalarda ihlal YOK.** LAB-00, kursiyerden depo
belgelerini dürüstlük kuralına karşı denetlemesini ister. Laboratuvarın hedef dosyaları
(`SECURITY_TESTS_TR.md`, `README.md`) fiilen tarandı. Sonuç: yasaklı ifadeler bu dosyalarda
**yalnızca olumsuzlanmış biçimde** geçiyor — sözcük eşlemesinin verdiği altı adayın altısı da
olumsuzlama:

- `SECURITY_TESTS_TR.md:10` — "hiçbir madde 'kanıtlanmış / kırılamaz / %100 güvenli' anlamına **gelmez**"
- `:26` — "'%100 doğruluk' iddiası **edilmez**"
- `:42` — "**%100 koruma mümkün değildir**"
- `:48` — "…gibi bir garanti **yazılmaz**"
- `:55` — "Bu yüzden 'sıfır risk' denmez"
- `:62` — "'kökten imkânsız' olduğu **söylenemez**"

`README.md:107` de "hardened / enterprise-grade / production-ready" etiketlerinin
**kullanılmadığını** açıkça yazar. Yani bu iki dosya `docs/UI_UX_STANDARD.md` §2.6'yı
çiğnemiyor, **örnekliyor**.

Bu, LAB-00'ın asıl dersidir ve K6 ile aynı derstir: `grep "%100"` burada **altı
yanlış-pozitif** üretir. Bir ihlal iddiası sözcüğün varlığına değil, cümlenin olumlama mı
olumsuzlama mı olduğuna dayanmalıdır — dedektörün "yersiz sinyal" arıza modu (§K6) tam olarak
budur. Bu yüzden LAB-00'ın ölçütü "en az N ihlal bul" **değildir**.

**10.7 Bu belgenin kendi sınırı.** §7.2'deki dış atıfların bir kısmı `[DOĞRULANMALI]`
etiketlidir ve **öyle kalmalıdır** ki okuyucu neyin teyit edildiğini bilsin. Program
materyali yayımlanmadan önce bu etiketler ya birincil kaynakla kaldırılmalı ya da atıf
tümüyle çıkarılmalıdır. Etiketi sessizce silmek, bu programın öğrettiği her şeye aykırıdır.

---

<!-- Üretim damgası (şeffaflık): Bu belge, depodaki kaynak belgeler ve kod okunarak
     hazırlandı (README, KURALLAR, PROJECT_BRIEF, THREAT_MODEL, UI_UX_STANDARD,
     AGENT_BRIDGE, FLOW_CONTROL_TR, ADR 0001-0003, SECURITY_BENCHMARK, MODEL_SECIMI_TR,
     MODEL_BENCH_hermes3-8b, KASA_DENETIM_VE_PROJEKSIYON_2026-08-01,
     OLCUM_BUTUNLUGU_VIZYON_2026-08-02, MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02,
     SECURITY_TESTS_TR + src/mcp_server, src/vault, src/agent, src/distill, src/dashboard,
     tools/, tests/, _orch/redteam/). Yazılan her iç dosya yolunun varlığı kontrol edildi;
     satır numaraları grep ile doğrulandı. Dış atıflarda emin olunmayan künyeler
     [DOĞRULANMALI] etiketlidir. Hiçbir test koşulmadı, hiçbir kaynak dosya değiştirilmedi.
     Tarih: 2026-08-03. -->
