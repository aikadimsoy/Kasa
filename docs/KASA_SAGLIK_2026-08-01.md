# KASA — Sağlık ve Eksik Analizi

_Ölçüm tarihi: 2026-08-01 04:15–04:35 · Yöntem: salt-okunur ölçüm + testlerin fiilen
koşturulması. Hiçbir KASA dosyası değiştirilmedi._

## Kısa cevap

**KASA stabil.** Test paketi tam yeşil, veritabanı bütün, rollback mekanizması fiilen
çalışıyor. Ama **üç eksik var ve ikisi "sessiz" cinsten** — yani sistem çalışıyor
görünürken yanlış bilgi veriyorlar. Sessiz eksikler, gürültülü hatalardan tehlikelidir.

## 1. Ölçülenler (kanıt)

| Ölçüm | Sonuç | Kanıt |
|---|---|---|
| Test paketi (30 dosya) | **192 passed, 1 xfailed** (56.3 sn) | `py -m pytest tests -q` |
| SQLite bütünlüğü | `integrity_check = ok` | `PRAGMA integrity_check` |
| DB içeriği | audit 92, events 77, permissions 1, profile 6 satır (0.76 MB) | doğrudan sorgu |
| Rollback davranışı | orijinal dosya geri yüklendi ✓, iş `blocked` ✓ | `selftest_rollback.py` koşusu |
| `.bak` üretimi | 2 yedek üretildi (`04:25:50`, `04:25:52`) | `_bak_archive/` içinde mevcut |
| İş panosu | 8 iş: 3 regression-watch, 3 pending, 1 green, 1 blocked | `_orch/loop/board.json` |

Test paketinin kapsamı ciddi: `test_advanced_redteam`, `test_delimiter_breakout`,
`test_semantic_injection`, `test_distill_injection`, `test_l4_toctou_gate`,
`test_drift_canary`, `test_agent_race` — yani enjeksiyon, yarış koşulu ve sürüklenme
sınıfları gerçekten test edilmiş. Bu, "testler var" ile "doğru şeyler test edilmiş"
arasındaki farkı geçiyor.

## 2. Bulgu #1 — Rollback selftest YANLIŞ KIRMIZI veriyor (sessiz eksik)

`selftest_rollback.py` çalıştırıldığında **`SONUC: FAIL`** basıyor. Ama mekanizma bozuk
değil — **testin kendisi bayat.**

Üç iddiadan ikisi geçiyor, biri kalıyor:

```
outcome        = blocked (beklenen: blocked)      ✓
target restored= True    (beklenen: True)          ✓   <- GÜVENLİK ÖZELLİĞİ ÇALIŞIYOR
splice+bak     = False   (beklenen: True)          ✗   <- testin baktığı yer yanlış
```

Kök neden: [selftest_rollback.py:59](../_orch/loop/selftest_rollback.py#L59) `.bak`
dosyasını **hedefin yanında** (`<repo>/src/`) arıyor:

```python
baks = [x for x in os.listdir(os.path.join(repo, "src")) if ".bak_loop_" in x]
```

Motor ise `.bak`'ı **merkezi arşive** taşıyor. Bugünkü koşunun iki yedeği
`D:\kasa\_bak_archive\` içinde, `04:25:48` damgalı olarak duruyor:
`target.py.bak_loop_20260801_042550`, `target.py.bak_loop_20260801_042552`.

**Neden önemli:** Bu, güvenlik mekanizmasının kanıtını üreten testtir. Sürekli FAIL
veren bir test, insanı "o zaten hep kırmızı" demeye alıştırır — ve gerçekten bozulduğu
gün fark edilmez. Kırmızı ışığın yanlış olması, olmamasından kötüdür.

**Düzeltme (tek satır):** testin `_bak_archive/` konumuna da bakması.

## 3. Bulgu #2 — Selftest üretim arşivini kirletiyor

Selftest geçici bir repo (`tempfile.mkdtemp`) kuruyor ve sonunda `shutil.rmtree` ile
siliyor. Ama ürettiği `.bak` dosyaları geçici dizine değil **gerçek**
`D:\kasa\_bak_archive\` dizinine düşüyor ve orada kalıyor. Yani her selftest koşusu
üretim yedek arşivine iki çöp kayıt bırakıyor.

Zararsız görünüyor ama arşiv "basename başına son N" mantığıyla budanıyorsa, selftest
çöpü **gerçek yedekleri arşivden dışarı itebilir**. Testin üretim durumuna dokunmaması
gerekir.

## 4. Bulgu #3 — İş panosu bayat durum taşıyor

`board.json` içindeki `tracker-request-block-paranoid` işi **`blocked`** görünüyor ve
`last_error` alanı **boş** — yani neden bloklandığı kayıtlı değil.

Ama iş fiilen **bitmiş**:

- Guard needle'ları kodda var: `KASA_TRACKER_DOMAINS` ve
  `XMLHttpRequest.prototype.open` → [browser_window.py](../src/browser/browser_window.py)
  içinde 4 eşleşme
- Testi geçiyor: `tests/test_tracker_block_paranoid.py` → **4 passed**
- Dahası bu test `board.json`'un `regression_always` listesinde, yani her koşuda
  yeşil doğrulanıyor

Pano durum deposu (state store) olduğu için, gerçekle uyuşmayan bir pano "hangi işler
kaldı?" sorusuna yanlış cevap verir. `blocked` + boş sebep kombinasyonu ayrıca şunu
gösteriyor: **blocked yazılırken sebep kaydı garanti altına alınmamış.** Sebepsiz
blocked, üç ay sonra çözülemez.

## 5. Eksik olmayan ama not düşülecek

- **`kasa_browser.pid` 25.6 gün bayat** — içindeki PID 12388 canlı değil. Çift-daemon
  olayının (WebAjans'ta belgelenmiş) KASA'daki karşılığı burada da mümkün: PID dosyası
  canlılık kanıtı değil. Heartbeat'li kilit deseni WebAjans'ta çözüldü, KASA'ya
  taşınabilir.
- **Veritabanı `journal_mode = delete`** — WAL değil. Tek yazıcı için sorun değil, ama
  eşzamanlı okuma/yazma ihtiyacı doğarsa WAL'a geçmek gerekir.

## 6. Araştırma altyapısı olarak KASA — değerlendirme

Bu oturumda KASA'nın `_orch` deseni yeni bir araştırma hattı kurmak için **şablon
olarak kullanıldı** ve iyi taşıdı. Taşınan parçalar:

| KASA parçası | Araştırma hattındaki karşılığı |
|---|---|
| `board.json` = durum deposu | parça bazlı iş panosu, devam-edilebilir |
| `guard.py` = deterministik doğrulama | JSON şema + **uydurma-kaynak kapısı** |
| `model_pipe.py` = taslak→inceleme | tek model + kod tarafı doğrulama |
| fail-closed (Ollama kapalıysa dur) | aynen korundu, exit 2 |
| üçlü olay çıkışı | `03_olaylar.jsonl` + board + log |

Desenin en değerli tarafı şu çıktı: **modelin "geçti" deme yetkisi yok.** Araştırma
hattında bu, modelin uydurduğu kaynak URL'lerini yakalayan bir kapıya dönüştü —
model bir iddiayı gerçek olmayan bir kaynağa bağlarsa kayıt reddediliyor.

`12_research_prompt_refiner.py` (deepseek genişletir → qwen netleştirir) deseni de
doğrudan kullanılabilir durumda; bu oturumda sorgu üretimi yerine **kaynak süzme**
için uyarlandı.

## 7. Öneri sırası

1. **Selftest'i düzelt** (Bulgu #1) — tek satır, ama güvenlik kanıtının kendisi.
   Aynı düzeltmede selftest'in üretim arşivine yazmasını da kes (Bulgu #2).
2. **Panoyu gerçekle senkronla** (Bulgu #3) — `tracker-request-block-paranoid` yeşile
   çekilmeli; ayrıca `blocked` yazan kod yoluna **sebep zorunluluğu** eklenmeli
   (sebepsiz blocked yazılamasın).
3. **PID → heartbeat'li kilit** — WebAjans'ta çözülmüş desen, buraya taşınabilir.

Hiçbiri acil değil; KASA şu an güvenli çalışıyor. Ama 1 ve 3 "sessiz" sınıfta, yani
zamanla güven aşındırırlar.
