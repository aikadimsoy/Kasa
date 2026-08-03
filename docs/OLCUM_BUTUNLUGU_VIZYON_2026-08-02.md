# Ölçüm Bütünlüğü — Araştırma Sentezi ve Vizyon Değerlendirmesi

_2026-08-02 · Yöntem: 6 paralel araştırma merceği + bağımsız eksik-kritiği ajanı; iddialar
Controller tarafından denetlendi, iki tanesi ölçümle **çürütüldü**. Sentez ve karar
Controller'a aittir; ajanlara sentez yasağı konmuştu._

---

## 0. Bu belgenin kendisi bir kanıt üretti

Araştırmayı kurarken kritik ajanına giden veriyi `slice(0, 60000)` ile kestim ve
**kesildiğini söyleyen bir alan koymadım.** Kritik ajanı bunu ilk maddesinde yakaladı:

> _"Bana altı mercek denildi, iki mercek geldi. (…) Bu, görevin konusunun canlı örneği:
> girdi sessizce kesildi, kesildiğini söyleyen bir alan yoktu."_

Yani incelediğimiz hatayı, o hatayı incelemek için kurduğum düzenekte tekrarladım. Bu,
raporun geri kalanındaki en ikna edici kanıttır: desen kişisel dikkatsizlik değil,
**varsayılan davranış**.

---

## 1. Desenin adı var — ve 22 yıllık

Avizienis, Laprie, Randell, Landwehr (IEEE TDSC, 2004) arıza modlarını dört eksende
sınıflar; bizi ilgilendiren eksen **detectability**:

> _"When losses are detected and signaled by a warning signal, signaled failures occur;
> otherwise, they are **unsignaled failures**."_

Ve aynı makale, doğrudan **ölçüm aletinin kendisi** hakkında şunu yazar:

> _"The detecting mechanisms themselves have two failure modes: 1) signaling a loss of
> function when no failure has actually occurred, that is a **false alarm**, 2) not
> signaling a function loss, that is an **unsignaled failure**."_

Yani "alet bozulur" fikri 2004'te formelleştirilmiş. Yazılım araç zincirlerinde neredeyse
hiç kullanılmıyor.

---

## 2. Ama çerçevemiz yanlış eksendeydi — kritiğin en değerli bulgusu

Sentezi "sessiz arıza" üzerine kurmuştum. Kritik ajanı vakaları yönlerine ayırdı:

| # | Bulgu | Yön |
|---|---|---|
| 1 | Gösterge hep "çalışıyor" | Sabitlenmiş sinyal |
| 2 | Timeout → "KRİTİK AÇIK" | **Yanlış alarm** |
| 3 | Boş stdout, rc=0 | Sessiz |
| 4 | Öz-test kalıcı FAIL | **Yanlış alarm** |
| 5 | Biten iş "blocked" | **Yanlış alarm** |
| 6 | Hız sınırı frenlemiyor | Sessiz |

**Vakaların yarısı yanlış alarm.** Gerçek desen "sessizlik" değil:
**dedektör çıktısının gerçeklikle bağının kopması — her iki yönde.**

Pratik sonucu var: dead man's switch, `absent()`, watchdog gibi karşı-önlemler yalnız
sessizlik yönünü kapatır. Yanlış-alarm yönü için başka malzeme gerekir (NIST SP 800-90B'nin
2⁻²⁰ yanlış-pozitif bütçesi, QARTOD "suspect / not evaluated" bayrakları, ISO 26262 LFM).

Kritiğin ikinci düzeltmesi de kabul edilmeli: **fail-stop bizim 3. hatamızı çözmez.** Süreç
zaten temiz çıkıyor; sorun çıkışta değil **yükte**. Doğru çerçeve "her bileşen dursun" değil,
**"her çıktı kendi geçerlilik iddiasını taşısın"**.

---

## 3. Ölçülmüş düzeltme: `subprocess` gerçekte ne yapıyor

Kendi iddiam iki noktada yanlıştı; ölçtüm:

| İddia | Gerçek (ölçüldü) |
|---|---|
| stdout boş dize döner | `stdout = **None**` |
| İstisna yutulur | Traceback **ebeveynin stderr'ine basılır**; çağırana gitmez |
| — | `returncode = **0**` — çocuk süreç başarılı |

Bu, vakayı zayıflatmıyor, **keskinleştiriyor**: sinyal vardır ama sonuçla hiçbir yerde
ilişkilendirilmeyen bir kanala düşer. Üstelik bizim kodumuz `(proc.stdout or "")` yazarak
`None` ile `""` ayrımını **ikinci bir katmanda** siler. Tek bir baytlık bilgi — "bu değer
geçerli mi" — iki kez atılır.

---

## 4. Her olgun alan bunu çözmüş; yazılım güvenliği istisna

"Ölçemedim" için **üçüncü durum**, aşağıdaki alanların hepsinde zorunlu:

| Alan | Ayrım |
|---|---|
| Yangın alarmı (NFPA 72) | ALARM / SUPERVISORY / **TROUBLE** (sistemin kendisi bozuk) |
| Proses alarmı (ISA-18.2) | 7 durum; **üçü** "alarm çalışmıyor" |
| Tıbbi cihaz (IEC 60601-1-8) | Fizyolojik ≠ **teknik** alarm koşulu |
| Havacılık veri yolu (ARINC 429) | Her veri kelimesinde **SSM** geçerlilik biti |
| Endüstriyel otomasyon (OPC) | Good / **Uncertain** / Bad |
| İzleme (Nagios) | Çıkış 3 = **UNKNOWN**, OK/WARN/CRIT'ten ayrı |
| Test (NUnit) | **Inconclusive** = "eldeki veriyle karar veremedim" |
| Test (pytest) | `failure` ≠ `error`; çıkış **5** = hiç test toplanmadı |
| Tedarik zinciri (SPDX) | **NONE** ("baktım, yok") ≠ **NOASSERTION** ("iddia etmiyorum") |
| Zafiyet (VEX) | "under investigation" — CycloneDX'te **varsayılan** |
| Uyum (SCAP/XCCDF) | "ölçülmedi" için **dokuz** değerli taksonomi |
| Kripto modül (FIPS 140-3) | Öz-test geçmezse **çıktıyı kapat** |
| Fonksiyonel güvenlik (ISO 26262) | **Latent Fault Metric** — mekanizmanın kendi gizli arızası, sayısal hedefle |
| **Muhasebe denetimi** | unqualified / qualified / adverse / **disclaimer of opinion** |

Sonuncusu en çarpıcısı: **"görüş bildiremiyorum"**, bugün eklediğim `DOĞRULANMADI` durumunun
yüzyıllık, hukuken bağlayıcı karşılığıdır. Denetçi ölçemediğinde "temiz" demez.

İstatistikte de karşılığı var: boş çıktıyı "0 bulgu" saymak, **MNAR'ı MCAR sanmaktır**.
Analitik kimyada "non-detect ≠ 0" bir sayı ve yöntem meselesidir (LOD/LOQ). Ve tek cümlelik
ata: _"Absence of evidence is not evidence of absence"_ (Altman & Bland, BMJ 1995).

---

## 5. Gerçek boşluk: KAPSAM

SARIF ayrımı yapıyor (`executionSuccessful`, `toolExecutionNotifications` ≠ `results`) ve
`executionSuccessful` **zorunlu** alan. Ama:

- **SARIF'te kapsam alanı YOK.** "1000 dosyanın 940'ına baktım" diyecek standart yer yok.
  GitHub'ın "taranan dosya yüzdesi" ve CodeQL'in `export-diagnostics`'i **ürüne özel**.
- **Tüketiciler ayrımı düşürüyor.** GitHub Code Scanning `result.kind` alanını yıllarca hiç
  uygulamadı, tüm sonuçları `fail` saydı. GitLab'de iş başarısızsa rapor **hiç alınmıyor**.
- **İzleme katmanı için LFM analoğu yok.** ISO 26262 güvenlik mekanizmasının kendi gizli
  arızasına sayısal hedef koyar (LFM ≥ %60/80/90). Yazılım gözlemlenebilirliğinde
  _"alarm kurallarımın kaçta kaçının sessizce ölmesi tespit edilebilir?"_ sorusunun ne adı
  ne ölçüsü var.

Bu üçü, KASA'nın somut katkı yapabileceği yer. Bugün `DOĞRULANMADI` diyebiliyoruz ama
**ne kadarının ölçüldüğünü** söyleyemiyoruz — tam da standardın boş bıraktığı yer.

---

## 6. Sayılar: talep var mı?

**Var, ama zorlayıcı kaydı.**

Lehte:
- Kanıt-üretim otomasyonu kanıtlanmış kategori: **Vanta 300M$ ARR**, 16.000+ müşteri;
  **Drata 100M$+ ARR**. GDPR Md. 5(2) ispat yükünü veri sorumlusuna kaydırıyor — hukuki temel.
- UK "AI assurance"ı ayrı sektör sayıyor: **524 firma, 1,01 milyar £** (2024).
- Ajan denetim izi talebi somut: kuruluşların **%92'si** ajan kimliklerini göremiyor,
  **%95'i** ele geçirilmiş bir ajanı tespit edebileceğinden şüpheli. Singapur, ajan başına
  doğrulanabilir kimlik + denetim izi şart koşan ilk çerçeveyi yayımladı.
- NIST SP 800-53 **AU-5** ve PCI DSS v4.0 **10.7.2**: "denetim mekanizmasının arızası"
  başlı başına raporlanabilir/alarm gerektiren bir olay.

Aleyhte — ve bunlar ciddi:
- **EU AI Act yüksek-risk yükümlülükleri ERTELENDİ**: Annex III 2 Aralık 2027, Annex I
  2 Ağustos 2028. Sayacağım zorlayıcı 18 ay kaydı.
- **ABD federal attestation zorunluluğu İLGA EDİLDİ** (OMB M-26-05, 23 Ocak 2026).
- **"Aletin sustuğunu söyleyen alet" için pazar kategorisi YOK.** Analist raporu, TAM
  tahmini, satıcı listesi yok. En yakın komşu (dead man's switch araçları) çok düşük ACV.
- Provenance adopsiyonu ince: en çok indirilen npm paketlerinin yalnız **%12,6'sı**.
- Yerel-öncelikli yazılımın pazar büyüklüğü verisi **kamuya açık değil**.
- ISO/IEC 42001 sertifikalı kuruluş sayısı **~350** (Nisan 2026) — kategori henüz çok küçük.

---

## 7. Alarm körlüğü: gerçek ama uçurum değil

Denetim raporumda "en tehlikeli bulgu" derken dayandığım şey doğrulandı **ama nüanslandı**:

- ICU alarmlarında yanlış pozitif **%67–95**; kritik alarmların yalnız **%26'sına** 90 saniye
  içinde yanıt veriliyor. Joint Commission: 3,5 yılda 98 olay, **80'i ölüm**.
- Google Tricorder'da bir analizörün yayında kalması için "efektif yanlış pozitif" oranı
  **%10'un altında** olmak zorunda — üretimde uygulanan somut eşik.

Ama:
- **"Şu oranı geçince operatör tüm alarmları yok sayar" biçiminde bir uçurum eşiği
  hakemli literatürde YOK.** Bulunan şey sürekli bir orantı yasası: insanlar alarmlara
  algıladıkları gerçek-alarm olasılığıyla **orantılı** yanıt verir (probability matching).
- Cry-wolf sahada tartışmalı: hava trafik kontrolünde **%47** sahte uyarı oranına rağmen
  ölçülebilir cry-wolf bulunamamış.

Yani: yanlış alarm zarar verir, ama "bir eşiği geçince çöker" demek fazla iddialı olur.
Doğru ifade **doğrusal aşınma**.

Kanonik vakalar deseni birebir doğruluyor: **Three Mile Island** — gösterge vananın
*konumunu* değil, vanaya gönderilen *komutu* gösteriyordu. **Air France 447** — stall
uyarısı hız 60 knot altına düşünce "geçersiz" sayılıp **sustu**, ve sessizlik pilot için
"tehlike yok" anlamına geldi. **Deepwater Horizon** — genel alarm ~bir yıl "inhibited"
modda tutulmuştu.

---

## 8. Karşı-bulgu: kendi tezimizi zayıflatan şey

Kritik ajanı, hiçbir merceğin fark etmediği bir şeyi gördü. "Mühür = ölçüm" ilkesi ölçümü
doğrudan **hedef** yapar; Goodhart yasasına göre bu, aletin sessizce *geçmesini*
ödüllendirmeliydi. Ama KASA'nın kendi verisi bunu **çürütüyor**: vakaların çoğu
yanlış-yeşil değil **yanlış-kırmızı**. Yani aletimiz kandırılmıyor, **kötümser bozuluyor**.

Bu iyi haber — ama izlenmeli. Yanlış-kırmızı bolluğu tam da alarm körlüğünü besleyen şey.

---

## 9. Vizyon değerlendirmesi — üç seçenek, bir öneri

### (A) Statüko+ : KASA hafıza kasası kalır, aletleri iyileşir
En düşük risk. Ama bir ay önce yazdığımız "boş hücre" iddiası artık geçersiz: Mem0'ın
OpenMemory'si, `the-vault`, `memory-vault` aynı işi yapıyor. **Yerel olmak artık fark değil.**

### (C) Ölçüm-bütünlüğü katmanını ayrı ürün yapmak
Entelektüel olarak en çekici, **ticari olarak en zayıf**: pazar kategorisi yok, analist
kapsaması yok, en yakın komşunun ACV'si çok düşük. Var olmayan bir kategoriye ürün satmak
en zor iştir. **Önermiyorum** — ama **iç disiplin** olarak korunmalı.

### (B) KASA'yı "denetlenebilir hafıza" olarak konumlamak ← ÖNERİM
Rakipler **hafıza katmanı**; KASA **kanıt üreten** hafıza katmanı. Fark artık gizlilikte
değil, **ispatlanabilirlikte**.

Gerekçeler:
1. **Hazır bir kelime dağarcığı var.** Dört-durumlu denetim görüşü
   (temiz / şartlı / olumsuz / **görüş bildiremiyorum**) hem hukuken tanınmış hem de KASA'nın
   hedef kitlesine tanıdık. Bugün eklediğim üç-durumlu karar bunun alt kümesi.
2. **Zorlayıcı bugün de var.** EU AI Act ertelendi ama GDPR Md. 5(2) hesap verebilirliği
   yürürlükte; DORA grace period'suz; Singapur ajan çerçevesi doğrudan "hangi ajan kimin
   yetkisiyle" izini şart koşuyor.
3. **Ölçülmüş boşluk somut.** %92 ajan kimliğini göremiyor, %95 ele geçirilmiş ajanı
   yakalayamayacağından şüpheli — ve KASA'nın P1 fazı (kimlik bağlama) tam bu.
4. **Standart boşluğu bir katkı fırsatı.** SARIF'te kapsam alanı yok. KASA'nın
   "ne kadarını ölçtük" alanını üretmesi, kredibilite açısından pazarlama bütçesinden
   değerli.

Dürüst sınır: bu bir **konumlandırma** kararıdır, ürün kararı değil. Kod tarafında karşılığı
üç şeydir — kimlik bağlama (P1), egress ölçümü (P2), ve her raporun kapsamını beyan etmesi.

---

## 10. Somut iş listesi (araştırmadan türeyen)

| # | İş | Dayanak |
|---|---|---|
| Ö1 | `(proc.stdout or "")` desenini temizle — `None` ≠ `""` ayrımını koru | §3, ölçüldü |
| Ö2 | Rapora **kapsam** alanı ekle: kaç kontrol koştu / kaç dosya tarandı | §5, SARIF boşluğu |
| Ö3 | Pozitif kontrol artefaktı yerleştir (EICAR/GTUBE mantığı): tarayıcı **bilerek** bulması gereken bir işaret bulamıyorsa alet bozuktur | §4, iyi yerleşmiş desen |
| Ö4 | Yanlış-alarm yönü için bütçe: her kontrolün yanlış-pozitif oranı izlensin (Tricorder %10 eşiği) | §2, §7 |
| Ö5 | Dört-durumlu karar sözlüğünü benimse (denetim görüşü şablonu) | §4, §9 |
| Ö6 | Tarama kapsamını düzelt: 3,7 GB derleme çıktısı → ~2 MB kaynak | kök neden, hâlâ açık |

---

<!-- Araştırma: 6 mercek + 1 eksik-kritiği ajanı, ~590K token. Sentez, düzeltmeler ve
     karar Controller (Opus 5). İki iddia ölçümle çürütüldü ve düzeltildi (§2, §3).
     Ajanlara sentez yasağı konmuştu; vizyon değerlendirmesi delege EDİLMEDİ. -->
