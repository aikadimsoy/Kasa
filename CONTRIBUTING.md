# KASA'ya Katkı Rehberi

Teşekkürler. KASA yerel-öncelikli, şifreli bir kişisel hafıza kasası ve ajanlara MCP
üzerinden **izin-aracılı** erişim veriyor. Bu yüzden buradaki katkı kuralları normal bir
Python projesinden biraz farklı: **ölçüm, iddiadan önce gelir.**

Bu belge; geliştirme kurulumu, test koşma, kod stili, dürüstlük kuralı, telif/lisans ve
issue/PR beklentilerini kapsar. Güvenlik **zafiyeti** bildirmek istiyorsanız buraya değil,
[`SECURITY.md`](SECURITY.md)'ye bakın — açık issue açmayın.

---

## 1. Geliştirme kurulumu

### 1.1 Python sürümü — derleme için 3.12 zorunlu

**Python 3.12 kullanın.** Bu bir tercih değil, ölçülmüş bir kısıt.
Kaynak: [`build_kasa.ps1`](build_kasa.ps1) satır 10 ve 30-31 — derleme betiği sürümü
doğruluyor ve 3.12 değilse **hata fırlatıp duruyor**; ayrıca `pyproject.toml`
`requires-python = ">=3.12,<3.13"`.

Ölçümün **tam** kapsamı şudur, olduğundan geniş yazmıyorum: segfault, Nuitka ile
**derlenmiş** exe'de pywebview penceresi açılırken görüldü ve kök nedeni Nuitka'nın
deneysel 3.14 desteği olarak kaydedildi (`docs/EXE_PACKAGING_LOG.md`, Spike-2: "Py3.14
SEGFAULT (exit 3) — deneysel-3.14 Nuitka bug'ı"; aynı spike Py3.12'de PASS). Yani ölçüme
dayanan şey **derleme** kısıtıdır. Depoda gündelik koşum bir süredir 3.14 üzerinde
yapılmış (aynı günlükte "Python: 3.14 (aktif)"; `docs/SECURITY_BENCHMARK.md` damgası
3.14.5). Derliyorsanız 3.12 **zorunlu**; yalnız kaynaktan koşuyorsanız hangi sürümde
olduğunuzu yazın (bkz. §2).

```powershell
# depo kökünde
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt
```

`requirements.txt` içeriği kasıtlı olarak kısa: `fastapi`, `uvicorn`, `pydantic`, `PyQt5`,
`cryptography`, `mcp`. Yeni bir bağımlılık eklemek **ayrı bir tartışma** ister (aşağıda §6).

### 1.2 Ollama (yerel model çalışma zamanı)

KASA'nın damıtma/zenginleştirme ve ajan katmanı **yerel** bir Ollama sunucusuna bağlanır.
Bulut model çağrısı yoktur ve eklenmemelidir.

- Varsayılan uç: `http://localhost:11434` — `src/config.py:19`, `kasa.toml.example:16`
- Varsayılan model: `qwen2.5:7b` — `src/config.py:18`, `kasa.toml.example:15`
- Ajan modeli seçimi ayrı bir ölçüm işidir ve belgelidir:
  [`docs/MODEL_SECIMI_TR.md`](docs/MODEL_SECIMI_TR.md) (tezgah: `tools/model_bench/`,
  damgalar: `docs/MODEL_BENCH_*.md` / `docs/model_bench_*.json`).

Ollama kurulu değilse çekirdek testlerin çoğu yine koşar; model tezgahını koşamazsınız.

### 1.3 Yapılandırma

```powershell
Copy-Item kasa.toml.example kasa.toml
Copy-Item browser_config.json.example browser_config.json
```

`kasa.toml` ve `kasa.db` **asla commit edilmez** (kişisel veri + bearer token içerirler).

### 1.4 Çalıştırma

```powershell
py -3.12 run.py                 # tepsi uygulaması
py -3.12 run.py --no-tray       # yalnız MCP sunucusu (başsız)
py -3.12 run.py --distill-now   # tek damıtma turu koş ve çık
```

EXE derlemek (Nuitka, tek dosya): `pwsh -File build_kasa.ps1`.

---

## 2. Test koşma

Testlerin **ek** bağımlılıkları var ve bunlar bilerek `requirements.txt`'te değil (çalışma
zamanı bağımlılığı değiller). Kaynak: `pyproject.toml`,
`[project.optional-dependencies] test`:

```powershell
py -3.12 -m pip install pytest httpx pywebview
py -3.12 -m pytest tests/ -q --ignore=tests/browser
```

**Damga okuması:** `214 passed, 1 xfailed`
(kaynak: [`docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md`](docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md)
§2.6 regresyon satırı, 2026-08-02).

**Dürüstlük notu — hangi yorumlayıcı:** o damga aynı belgenin §5'inde yazılı komutla, yani
`py -3.14 -m pytest tests/ -q --ignore=tests/browser` ile alınmıştı; 3.12 ile aynı sayının
çıkacağı **ölçülmedi**. Aynı gün koşan güvenlik tezgahı da 3.14.5 üzerinde koştu
(`docs/SECURITY_BENCHMARK.md` başlık satırı). 3.12 kısıtının dayanağı derleme tarafıdır
(§1.1). Bu yüzden: sayıyı yazarken **hangi yorumlayıcıyla** koştuğunuzu da yazın.

Bu bir **damga**, kalıcı bir vaat değil. "Her zaman böyledir" demeyin ve bu sayıyı belge
diye kullanmayın; PR'ınızın tabanında **kendiniz koşup** kendi sayınızı yazın. Sayı
düştüyse sebebini yazın; düşmesi otomatik ret değil, **açıklanmamış** düşmesi rettir.

`tests/browser` dışarıda bırakılıyor çünkü canlı tarayıcı/WebView2 ve model gerektiriyor;
ayrı koşulur.

**Bilinen kısıt (depoyu başka bir yola klonlarsanız):** dört test dosyası depo kökünü
`d:/kasa` olarak **sabit** yazıp o yoldan dosya okuyor — `tests/test_browser_gate.py:6`,
`tests/test_kasa_health_hook.py:5`, `tests/test_terms_gate.py:82`,
`tests/test_tracker_block_paranoid.py:5` (ayrıca `tests/conftest.py:15`'teki `repo_root`
fikstürü aynı yolu döndürüyor; şu an hiçbir test onu kullanmıyor).
Import yolu `pyproject.toml`'daki
`pythonpath = ["."]` sayesinde çalışır, ama bu dosyaların dosya-yolu iddiaları başka bir
konumda tutmaz. Yani yukarıdaki sayı `d:\kasa` dışında birebir yeniden üretilemez. Kök
çözüm (yolu `Path(__file__)` ile türetmek) sahibin kararını bekliyor; tek başına bunu
düzelten bir PR gönderecekseniz önce issue açın.

Güvenlik tezgahı ayrı bir alettir ve testlerin yerine geçmez:
[`docs/SECURITY_BENCHMARK.md`](docs/SECURITY_BENCHMARK.md) onun çıktısıdır. Güvenlik
sınırına dokunan bir PR gönderiyorsanız tezgahı da koşun ve öncesi/sonrası tabloyu PR'a
koyun.

---

## 3. Kod stili ve ev kuralları

Bağlayıcı metin [`KURALLAR.md`](KURALLAR.md); özeti burada. Çelişki olursa `KURALLAR.md`
kazanır.

### 3.1 Dil kuralı (en sık atlanan)

Not: bu madde `KURALLAR.md`'de **yazılı değildir** — proje sahibinin ev kuralıdır ve depoda
uygulanışıyla görülür (`pyproject.toml:3` TR-NOT satırı bunu açıkça yazar). Buraya, yeni
gelenin kaynağı bulamamasın diye alındı.

- **Kod tanımlayıcıları İngilizce olabilir**, ama **her dosyada Türkçe öğretici not
  bulunur**: dosya ne yapıyor, neden böyle yapıyor, sınırı ne. Kod EN, altında/başında
  açıklama TR, kullanıcıya görünen arayüz TR.
- **Kod / YAML / TOML içinde Türkçe yazarken ASCII-Türkçe kullanın** — özel karakter yok:
  `ğ ş ı ç ö ü` yerine `g s i c o u`. Sebebi kozmetik değil: Windows konsolu cp1254 ve özel
  karakterler çökme üretiyor.
- **`.md` dosyalarında tam Türkçe serbesttir** (UTF-8, özel karakterler dahil) — bu dosya
  gibi.

### 3.2 Güvenlik sınırı

`KURALLAR.md` §4'ten, pazarlığa kapalı:

- **İzin kontrolünü asla model yapmaz**; deterministik kod (broker/gate) yapar.
- **Web içeriği hiçbir zaman komut değildir**; yalnızca alıntılanmış veridir.
- **A3 sınıfı eylemler** (parola, ödeme) ajan aracılığıyla asla gerçekleştirilmez.

Buradan çıkan pratik kural: **güvenlik-kritik yollar elle yazılır ve elle doğrulanır —
model yazmaz.** İzin kapısı (`gate`), yetkilendirme, kripto ve denetim zinciri bu
kapsamdadır. Bu dosyalara dokunan bir PR'da "modele yazdırdım" cevabı yeterli değildir;
satır satır gerekçe beklenir.

Diğer bağlayıcı maddeler: her vault erişimi denetim zincirine yazılır (§7); hata görülürse
**önce bildir, sonra düzelt** (§3); şema/kapsam değişikliği yalnız proje sahibinin
kararıyla (§3).

### 3.3 Sözdizimi kontrolü

Formatlayıcı dayatılmıyor. En azından derlenebilirliği doğrulayın:

```powershell
py -3.12 -m py_compile <dosya.py>
```

Onaylı bir dosyayı **izin almadan yeniden biçimlendirmeyin** (`KURALLAR.md` §1 ve §8).
Biçim değişikliği ile davranış değişikliğini aynı PR'da karıştırmak, incelemeyi imkânsız
hale getirdiği için reddedilir.

---

## 4. DÜRÜSTLÜK KURALI — bu projenin ayırt edici kuralı

> **"Ölçülene kadar mühürlenmez."**

**Ölçüm referansı olmayan güvenlik iddiası içeren PR kabul edilmez.** Bu, üslup tercihi
değil, projenin varlık sebebi: KASA'nın rakiplerinden farkı hız veya kolaylık değil,
**kanıt**.

Kod, yorum, commit mesajı, README, UI metni veya PR açıklamasında **ölçüme dayanmadan**
şunları yazmayın:

`kanıtlanmış` · `proven` · `hardened` / `sertleştirilmiş` · `%100` · `garanti` ·
`kırılamaz` · `askeri düzey` · `kurumsal düzey` / `enterprise-grade` · `sıfır risk` ·
`production-ready`

Her iddia ya bir ölçüme dayanır ya **hiç yazılmaz**. Kabul edilen dayanaklar:

- `dosya.py:satır` biçiminde somut kod referansı,
- geçen bir test adı (`tests/test_*.py::test_*`),
- `docs/` altındaki tarihli bir damga (ör. `docs/SECURITY_BENCHMARK.md` koşusu).

Doğru biçim şuna benzer:

- ❌ "Denetim zinciri kurcalamaya karşı korumalıdır, garanti."
- ✅ "Denetim zinciri kurcalamaya duyarlı: `AUDIT-TAMPER-MODIFY` ve `AUDIT-TAMPER-DELETE`
  PASS (`docs/SECURITY_BENCHMARK.md`, 2026-08-02 koşusu)."

İkinci cümle daha uzun ve daha zayıf görünüyor. Doğru olan o.

Aynı kural **negatif** yönde de geçerlidir: ölçemediğiniz bir şeyi "bozuk" diye de
işaretlemeyin. Denetim belgesi bunu projenin en tehlikeli bulgusu olarak kaydetti —
koşamayan bir kontrol `FAIL` değil, `ERROR`'dur; "bakamadım" ile "buldum" aynı kırmızıya
boyanırsa insan kırmızıya bakmayı bırakır
(`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §5).

---

## 5. Telif, lisans ve katkı beyanı

KASA **çift lisanslıdır**:

- **AGPL-3.0** — bireysel, eğitim ve araştırma kullanımı serbest. Kanonik metin depo
  kökündeki [`LICENSE`](LICENSE) dosyasıdır; **o dosyaya dokunmayın**.
- **Ticari lisans** — türev çalışmasını açmak istemeyen şirketler proje sahibinden ayrı bir
  ticari lisans alır (Sentry / Plausible ile aynı model). Şartlar ve gerekçe:
  [`COMMERCIAL.md`](COMMERCIAL.md).

Bunun katkıcı için tek pratik sonucu şudur ve sade haliyle yazıyorum:

> **Bir pull request gönderdiğinizde, katkınızın hem AGPL-3.0 altında hem de proje
> sahibinin ticari lisansı altında dağıtılabileceğini kabul etmiş sayılırsınız.**

Sebebi mekanik: çift lisans modeli, projenin tamamının her iki lisans altında da
dağıtılabilmesini gerektirir; tek bir katkı bunun dışında kalırsa model çalışmaz.
Telif hakkınız sizde kalır — devretmiyorsunuz, yalnızca bu iki kanaldan dağıtıma izin
vermiş oluyorsunuz.

Bunu kabul etmiyorsanız PR göndermeyin; bunun yerine issue açıp fikri tarif edin —
uygulamayı sahip yapar, kimse mağdur olmaz.

Attribution deposun içinde kalır: sahiplik ve kaynak bilgisi silinmez.

*(Not: burada resmî bir hukuki CLA metni yoktur ve uydurulmamıştır. Proje sahibi ileride
imzalı/otomatik bir CLA süreci eklemeye karar verebilir; bu bölüm o zamana kadar geçerli
olan sade beyandır.)*

---

## 6. Issue ve PR beklentileri

**Issue açarken:**

- Önce mevcut issue'lara ve `docs/` altına bakın — özellikle
  `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §7 (E1–E11 eksik listesi) ve
  `docs/SECURITY_BENCHMARK.md`. Bilinen eksiklerin çoğu zaten yazılı ve **öncelikli**.
- Hata bildiriminde: Windows sürümü, Python sürümü, tam hata çıktısı, yeniden üretme adımı.
- Özellik önerisinde: hangi problemi çözdüğü ve **hangi sınırı gevşetmediği**.

**PR gönderirken:**

- **Küçük ve tek konulu tutun.** Biçim + davranış karışımı PR'lar incelenemez.
- Şema, kapsam veya güvenlik sınırı değişikliği için **önce issue açın**; kod yazmadan önce
  sahip kararı gerekir (`KURALLAR.md` §3). Reddedilen büyük bir PR kimse için iyi değil.
- Testlerinizi ekleyin, sonucu PR'a yazın, güvenlik sınırına dokunduysanız tezgah çıktısını
  da ekleyin.
- Değiştirdiğiniz dosyada Türkçe öğretici notu güncelleyin — kod değişti, not bayat kaldıysa
  bu da bir hatadır.
- Yeni bağımlılık **gerekçe ister**: bu makinede C/Rust/Node derleme zinciri yoktur ve bu
  bilinçli bir kısıttır (`docs/UI_UX_STANDARD.md` §3, ADR-0003 fizibilite dersi). Saf-Python
  veya hazır wheel olmayan bağımlılıklar büyük olasılıkla reddedilir.
- Güvenlik **zafiyeti** düzeltmesini doğrudan public PR olarak göndermeyin —
  [`SECURITY.md`](SECURITY.md) akışını izleyin.

**Davranış.** Kısa tutuyorum, ayrı bir davranış kuralları dosyası yok: saygılı ve teknik
olun; eleştiri koda yöneliktir, kişiye değil. Anlaşmazlıkta ölçüme dönün — "bence" ile
"ölçtüm" arasındaki farkı bu proje ciddiye alır ve tartışmayı ölçüm bitirir. Taciz, kişisel
saldırı ve kasıtlı kötü niyetli katkı (gizli arka kapı, veri sızdıran kod) katılımın sona
ermesiyle sonuçlanır. Bir davranış sorununu bildirmek için depo sahibiyle özel kanaldan
iletişime geçin.

---

## English summary

**Setup.** Python **3.12 is required to build**: `build_kasa.ps1:30-31` refuses to build
without it and `pyproject.toml` pins `>=3.12,<3.13`. Scope of the measurement, stated
exactly: the segfault was observed in the *Nuitka-compiled* exe opening a pywebview window
and was root-caused to Nuitka's experimental 3.14 support (`docs/EXE_PACKAGING_LOG.md`,
Spike-2; the same spike passes on 3.12). Day-to-day runs in this repo have been on 3.14
(same log: "Python: 3.14 (aktif)"; the security bench stamp reads 3.14.5). Create a venv, then
`py -3.12 -m pip install -r requirements.txt`. A local **Ollama** runtime is expected at
`http://localhost:11434` with `qwen2.5:7b` as the configured default
(`src/config.py:18-19`); there are no cloud model calls and none should be added. Copy
`kasa.toml.example` → `kasa.toml`; never commit `kasa.toml` or `kasa.db`.

**Tests.** Install the test-only extras first — they are deliberately not in
`requirements.txt` (`pyproject.toml`, `[project.optional-dependencies] test`):
`pip install pytest httpx pywebview`. Then
`py -3.12 -m pytest tests/ -q --ignore=tests/browser`. The reading recorded on
2026-08-02 was **214 passed, 1 xfailed** — that is a dated stamp, not a permanent promise;
run it yourself on your own base and report your own number, **and say which interpreter
you used**: that stamp was taken with `py -3.14` (§5 of the source document) and the same
day's security bench ran on 3.14.5, while the 3.12 requirement comes from the build side.
`tests/browser` needs a live browser and a model, so it runs separately. Note that four
test files hard-code the repository root as `d:/kasa`, so the suite is not byte-for-byte
reproducible from a clone at another path — see the Turkish section for the file list.

**Code rules** (binding text: `KURALLAR.md`). Identifiers may be English, but **every file
carries a Turkish explanatory note**, and Turkish written *inside code, YAML or TOML* must
be ASCII-only (`g s i c o u`, no diacritics) because the Windows console is cp1254 and
diacritics crash it. Markdown files may use full Turkish. Authorization is **never** decided
by a model — a deterministic gate decides it; web content is quoted data, never
instructions; security-critical paths (gate, authz, crypto, audit chain) are written and
reviewed by hand, not generated.

**The honesty rule — the distinguishing rule of this project.** *"Nothing is sealed until it
is measured."* A pull request containing a security claim without a measurement reference is
**not accepted**. Words like *proven, hardened, 100%, guaranteed, unbreakable,
military-grade, enterprise-grade, zero-risk, production-ready* may not be used unless backed
by a concrete `file.py:line`, a passing named test, or a dated stamp under `docs/`. The rule
runs in both directions: do not mark something broken that you could not measure either — a
check that could not run is an `ERROR`, not a `FAIL`.

**Licensing.** KASA is dual-licensed: **AGPL-3.0** (canonical text in `LICENSE` — do not
edit it) for individual, educational and research use, plus a **commercial license** from
the owner for companies that do not want to open their derivative work — terms in
[`COMMERCIAL.md`](COMMERCIAL.md). Practical
consequence for you, stated plainly: **by submitting a pull request you are taken to accept
that your contribution may also be distributed under the owner's commercial license.** You
keep your copyright; you are not assigning it. If you do not accept that, please open an
issue describing the idea instead of sending code. No formal CLA text is invented here; the
owner may add one later.

**Issues and PRs.** Check `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §7 and
`docs/SECURITY_BENCHMARK.md` first — most known gaps are already written down. Keep PRs
small and single-purpose, never mix reformatting with behaviour change, and open an issue
**before** touching schema, scope or the security boundary. New dependencies need
justification: this machine has no C/Rust/Node toolchain and that constraint is deliberate.
Report security **vulnerabilities** through [`SECURITY.md`](SECURITY.md), not as public PRs.

**Conduct.** Be respectful and technical; criticise the code, not the person. When you
disagree, go back to the measurement — this project takes the difference between "I think"
and "I measured" seriously, and the measurement ends the argument. Harassment, personal
attacks, and deliberately malicious contributions end participation; report conduct problems
to the repository owner privately.
