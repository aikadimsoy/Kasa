# Proje KASA

Windows'ta Ajan Tabanlı Tarama için Egemen, Yerel-Öncelikli bir Hafıza Kasası

## Sorun

Bugünkü ajan tabanlı tarayıcılar, kalıcı kullanıcı hafızasını satıcı bulutlarında saklıyor; bu da ciddi gizlilik ve kontrol sorunları doğuruyor. Kullanıcılar tarama verilerine sahip olamıyor ve yapay zekâ ajanlarına izin vermenin yasal sonuçları net biçimde tanımlanmış değil. Bu proje, herhangi bir ajanın izin-aracılı bir MCP (Model Context Protocol) sunucusu üzerinden erişebileceği; yerel-öncelikli, şifreli ve kullanıcıya ait bir hafıza kasası sağlayarak bu eksiklikleri gidermeyi amaçlıyor.

## KASA Ne Yapar

KASA, Windows kullanıcıları için egemen bir hafıza kasası olarak tasarlanmıştır: kasa dosyası, şifreleme anahtarı ve izin kararları kullanıcının makinesinde kalır. *Tam kontrol* iddia **edilmez** — ölçülmüş sınırlar (istemci beyanlı `agent_id`, ölçülmeyen egress, düz metin metadata kolonları) aşağıdaki Proje Durumu'nda adıyla yazılıdır. "Ajanlar gelip gider; hafızanız sizindir" ilkesine dayanır. Sistem şunları içerir:

- Hassas hücreleri diskte hücre başına AES-256-GCM ile şifreleyen yerel bir Hafıza Kasası. Dürüst kapsam: şifreleme üç kolonu kapsayan hücre bazlı şifrelemedir, tam-veritabanı değil — aşağıdaki Proje Durumu'na bakın.
- Bu kasayı, aracılı bir protokol üzerinden izin sahibi her ajana açan bir MCP Sunucusu.
- Yalnızca yetkili ajanların veriye erişmesini sağlayan, kullanıcı bilgisi üzerinde sıkı denetim kuran bir izin hesabı (permission calculus).

## Mimari

KASA'nın mimarisi beş ana bileşenden oluşur:

| Bileşen | Rol | MVP Durumu |
|---------|-----|------------|
| Hafıza Kasası | Yerel depo; hassas hücreler şifreli (AES-256-GCM), metadata kolonları düz metin | ✅ |
| MCP Sunucusu | Kasayı ajanlara açan localhost sunucusu | ✅ |
| Ajan Çekirdeği | Yerel model ve planlayıcı | ✅ (yalnızca damıtma) |
| İzin Aracısı | Dış erişim için deterministik geçit | ✅ (kapsam denetimleri) |
| Tarayıcı Uzantısı | Sayfaları okur, ileride eylem yürütür | Ertelendi |

### Tasarım Değişmezleri

1. **İnce Kenarlar, Kalın Çekirdek**: Uzantı hiçbir zekâ ve veri içermemeli; tüm durum yardımcı uygulamada tutulur.
2. **Model Güvenlik Sınırı Değildir**: Yetkilendirme kararları, sıradan kod içindeki İzin Aracısı tarafından verilir.
3. **Sayfa İçeriği Veridir, Komut Değildir**: Web'den gelen her metin alıntı verisi olarak etiketlenir. Hedefler yalnızca kullanıcının kendi komutlarından türetilebilir.

## Güvenlik

Bu depodaki her güvenlik iddiasının, dayandığı ölçümü adıyla göstermesi beklenir. Güncel kanıt
raporu [`docs/SECURITY_BENCHMARK.md`](docs/SECURITY_BENCHMARK.md) (21 kalem, her kalem için kanıt
dizesi), sınırları açıkça yazılmış test-test ayrıntı
[`SECURITY_TESTS_TR.md`](SECURITY_TESTS_TR.md), açık bulguları içeren bağımsız denetim ise
[`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md`](docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md).

- **Kırmızı takım bulguları — ne ölçüldü, ne hâlâ açık.** Her satır dayandığı kanıtı adıyla
  gösterir; hiçbiri "bu saldırı sınıfı çözüldü" demez.
  - *Damıtma zincirine dolaylı komut enjeksiyonu* — güvenilmeyen olay metni açık sınırlayıcılarla
    sarılır ve QC köken (provenance) geçidi, modelin kaynak gösteremediği fact'i reddeder. Ölçüm:
    `tests/test_distill_injection.py`, `tests/test_delimiter_breakout.py`,
    `tests/test_semantic_injection.py`. **Sınır:** komut enjeksiyonu sektör genelinde **açık** bir
    problemdir; buradaki savunma *yapısaldır* (model asla güvenlik sınırı değildir), bağışıklık
    iddiası değildir.
  - *MCP yetkilendirme* — izin-listesi (`PUBLIC_TOOLS`), rezerve-ajan bloğu ve kapsam başına
    varsayılan-red kontrolleri ölçümlerini geçiyor (`AUTHZ-*` kalemleri:
    [`docs/SECURITY_BENCHMARK.md`](docs/SECURITY_BENCHMARK.md); `tests/test_agent_gate.py`).
    **Hâlâ açık:** `agent_id` istemci-beyanlıdır; token sahibi başka bir ayrıcalıklı ajan kimliğini
    taklit edebilir ve denetim atfı sahtelenebilir — F-IMP bulgusu için bkz.
    [`SECURITY.md`](SECURITY.md) ve
    [`docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md`](docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md).
    Bu **kapatılmadı**.
  - *Otomatik test→düzelt döngüleri* — sıfır-maliyetli yerel-model döngüsü ve tarayıcı sağlık
    kapıları kontrolleri tekrar tekrar koşar (`_orch/loop/`, `tools/security_bench/`). Bunlar
    regresyon kapsamını artırır; tek başlarına güvenlik kanıtı **değildir**.

## Kurulum ve Çalıştırma

### Gereksinimler

- **Yalnızca Windows.** KASA bugün çapraz-platform değildir: tepsi uygulaması Windows'ta PyQt5 kullanır ve kasa anahtarı **Windows DPAPI** ile korunur. macOS/Linux'ta DPAPI katmanı bir no-op'tur, yani KASA'nın dayandığı anahtar koruması orada mevcut değildir (ölçülmüş sınır: `docs/SECURITY_BENCHMARK.md` → "Bilinen Sınırlar", *non-Windows DPAPI no-op*).
- **Python 3.12 — her zaman bunu kullanın.** Masaüstü yolu 3.12'ye sabitlenmiştir: Nuitka ile derlenmiş ikili, Python 3.14 altında pywebview penceresini açarken **segfault** veriyor. Bu varsayım değil, ölçüm — `docs/EXE_PACKAGING_LOG.md`, "Spike-2 Py3.14: SEGFAULT (exit 3)"; derleme script'i başka sürümü `build_kasa.ps1:29-32`'de reddediyor. Ölçümün dürüst kapsamı: bu, masaüstü/exe yolunda gözlendi; test paketi ve güvenlik tezgahının kendisi en son 3.14.5 altında koşturuldu (`docs/SECURITY_BENCHMARK.md` başlığı). 3.12 kullanmak bu soruyu tamamen ortadan kaldırır.
- **Ollama ayrıca kurulur.** KASA bir model çalışma zamanı paketlemez veya kurmaz. Damıtma çalışma zamanında isteğe bağlıdır; kasa ve pano o olmadan da çalışır.

### Adımlar

1. **Sanal ortam oluşturun** (önerilir; 3.12 sabitini de açıkça görünür kılar):
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. **Bağımlılıklar**: Gerekli Python paketlerini şu komutla yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
3. **Yerel Ollama Çalışma Zamanı** (isteğe bağlı, yalnız damıtma için gerekir): Ollama'yı https://ollama.com adresinden ayrıca kurun, ardından modeli çekin ve http://localhost:11434 adresinde servis verdiğinden emin olun:
   ```bash
   ollama pull qwen2.5:7b
   ```
4. **Yapılandırma**: `kasa.toml.example` dosyasını `kasa.toml` olarak kopyalayın ve sunucu host/port, kasa yolu gibi ayarları isteğinize göre düzenleyin. Bearer token ilk çalıştırmada üretilir.
5. **Sistem Tepsisi Uygulamasını Başlatma**: Uygulamayı şu komutla çalıştırın:
   ```bash
   python run.py
   ```
6. **Yalnızca MCP Sunucusu (Tepsisiz Mod)**: Tepsi simgesi olmadan yalnızca MCP sunucusunu çalıştırmak için:
   ```bash
   python run.py --no-tray
   ```
7. **Tek Bir Damıtma Turu Çalıştır ve Çık**: Tek bir damıtma turu çalıştırıp çıkmak için:
   ```bash
   python run.py --distill-now
   ```
8. **Şifreli Taşınabilir Dışa Aktarım**: Kasanızı şifreli bir dosya olarak dışa aktarmak için:
   ```bash
   python run.py export --output my_vault.kasa --verify
   ```

## MCP Araçları

KASA, yerel kullanım için şu MCP araçlarını sunar:

- `profile_read(scope)`, `profile_write(fact)`, `forget(topic)`, `audit_read(range)`, `event_ingest`, `prune_expired_events`.

## Test Etme

KASA test için pytest kullanır. Testleri çalıştırmak için:
```bash
pytest -q
```

## Proje Durumu

**Yayına hazır değil — ve bunu projenin kendisi söylüyor.** Güncel tezgah damgası
**"YAYINA HAZIR DEĞİL"** diyor: 21 kalemde **18 PASS · 1 FAIL · 2 WARN**
(`docs/SECURITY_BENCHMARK.md`, commit `2dfda9e`). Evin kuralı *ölçülene kadar mühürlenmez*;
bu yüzden "sertleştirilmiş", "kurumsal düzey" veya "üretime hazır" gibi etiketler burada
kullanılmaz — `docs/UI_UX_STANDARD.md` §2.6 bunları ampirik olarak ölçülene kadar yasaklar.

- **Uygulanan ve yeşil ölçülen:** MVP-0 güvenlik çekirdeği — kasa + MCP sunucusu + aracılı izinler
  + damıtma + denetim hash-zinciri. 7 `AUTHZ-*` kaleminin tamamı PASS (C5/C7/C8 ve `127.0.0.1`
  bağlanma denetimi dahil), 3 `AUDIT-*` zincir/kurcalama kalemi PASS, 5 `CRYPTO-*` kalemi PASS,
  2 `FUZZ-*` kalemi PASS, bağımlılık denetimi 0 açıklı bağımlılık raporluyor.
- **Kırmızı / sarı ölçülen:** `SCAN-SECRETS` **FAIL** — bearer token `kasa.toml` içinde düz metin
  duruyor; sahip-özel ACL uygulandı, rotasyon ve DPAPI-wrap hâlâ bekliyor. `SCAN-BANDIT` WARN
  (13 orta bulgu, triyaj edilmedi) ve `SCAN-BAK-HYGIENE` WARN.
- **Adı konmuş açık boşluklar**, ölçümü `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` içinde:
  (a) `agent_id` istemci beyanlıdır ve doğrulanmaz; bu yüzden hız sınırı baypas edilebiliyor ve
  **denetim atfı sahtelenebilir** (§4.1); (b) **çıkış (egress) ne kısıtlanıyor ne ölçülüyor** —
  `docs/GUVENLIK_CIKIS_PLANI.md` planı kurulmadı (§4.4); (c) at-rest şifreleme **üç kolonu kapsayan
  hücre bazlı** şifrelemedir, tam-veritabanı değil — metadata kolonları düz metin kalır (§1 ve
  `docs/adr/0003-at-rest-sifreleme-boslugu.md`).
- **Komut enjeksiyonu — dürüst çerçeve:** tüm sektörde hâlâ açık bir problem sınıfıdır.
  KASA'nın savunması *yapısaldır* (model asla güvenlik sınırı değildir; izin kapısı sıradan,
  deterministik koddur), bir dokunulmazlık iddiası değil.
- Tarayıcı uzantısı, web eylemleri (A1-A3), bulut maskeleme/yükseltme ve parmak izi sahteleme
  katmanı ertelendi / park edildi (MVP-0 kapsamı dışında).

Test test ayrıntı — ve her iddianın neyi kanıtlaMAdığı — burada:
[`SECURITY_TESTS_TR.md`](SECURITY_TESTS_TR.md).

## Lisans

KASA **çift lisanslıdır**:

- **AGPL-3.0** — bireysel, eğitim ve araştırma kullanımı için, ayrıca türev çalışmayı aynı koşullarla
  açık tutan her kullanım için serbesttir. Kanonik lisans metni: [`LICENSE`](LICENSE).
- **Ticari lisans** — türev çalışmasını AGPL altında yayımlamak istemeyen kurumlar içindir.
  Koşullar: [`COMMERCIAL.md`](COMMERCIAL.md).

Yazara atıf, her iki seçenekte de projede kalır.
