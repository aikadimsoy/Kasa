# KASA Alım Etiketleme ve İzleme Katmanı — Tasarım Planı **v4**

Tarih: 2026-08-01 · Durum: **PLAN — sahip onayı bekliyor** (KURALLAR §1/T1, §3/T3)
Kod kuralı: İngilizce tanımlayıcı + Türkçe açıklama notu (`docs/GUVENLIK_CIKIS_PLANI.md` §4).

> **Bir cümlede:** Ajanların dış kaynaklardan getirdiği içerik **reddedilmez, engellenmez,
> silinmez** — etiketlenir, kökeniyle izlenir ve insanın gün sonunda iki saniyede karar
> verebileceği bir listeye düşer.

---

## 1. Hedefler — amaç ve gerekçe

Her hedef: neyi istiyoruz (**amaç**), o olmazsa ne kırılır (**neden**), başarıldığını
nasıl bileceğiz (**ölçüt**). Ölçütsüz hedef yazılmaz — mühür ölçümün yan ürünüdür.

### H1 — Kirli kaynaklı içeriğin ajan çıktısını **sessizce** kirletmesini bitirmek

- **Amaç:** Dış kaynaktan gelen manipülatif/zehirli metnin üretilen içeriğe veya kalıcı
  profile fark edilmeden sızmasını engellemek; sızarsa **görünür** olmasını sağlamak.
- **Neden:** İçerik üreticisinin ajanı onlarca güvenilmeyen kaynağı tarar. KASA bugün
  kandırılan modelin *eylemini* (araç çağrısı, sızdırma) engelliyor ama *çıktısını*
  korumuyor. Ticari zarar tam buradan doğar: dolandırıcının linki "kaynak" diye yayına
  girer. Bu, mimarinin bilinen ve açık kalan tek büyük sınıfıdır.
- **Ölçüt:** Bilinen enjeksiyon korpusunda, kalıcı profile terfi eden zehirli iddia
  oranı ölçülür ve hedef eşiğin altında tutulur; her terfi olayı kökene kadar izlenebilir.

### H2 — Hiçbir meşru veriyi kaybetmemek

- **Amaç:** Hiçbir aşamada içerik reddedilmesin, silinmesin, gizlenmesin.
- **Neden:** İki bağımsız gerekçe. (a) `redact.py` bu kararı zaten vermiş: *"Reddetmez:
  meşru hafıza korunur… aşırı-agresif reddin yol açtığı kendine-DoS önlenir."* (b) Taban
  oranı aritmetiği (§7): ölçülen kesinlik %4 mertebesindeyse eylem "blok" olduğunda
  **20 blokajın 19'u meşru veri kaybıdır**. Zayıf detektörle pahalı eylem eşleştirilmez.
  Etiket sonradan düzeltilebilir; atılan veri geri gelmez.
- **Ölçüt:** Testler, hiçbir yolun içerik silmediğini/reddetmediğini doğrular (v3'ten
  beri değişmez). Kod incelemesinde "drop/reject" yolu bulunmaz.

### H3 — İnsanın iki saniyede karar verebileceği bir inceleme yüzeyi

- **Amaç:** Şüpheli maddeler, **bayrağın sebebi satırın kendisinde görünecek** biçimde
  listelensin (tarih, içerik özeti, kaynak, hedef, amaç-hipotezi, eksik olan kanıt).
- **Neden:** Etiketleme teknik olarak çalışıp insan tarafında ölebilir. Günde 200 satırlık
  gerekçesiz liste ilk hafta sonunda kapatılır. Satır kendini açıklarsa ("iddia: en iyisi
  / gerekçe: yok / karşılaştırma: yok / kaynak: tek") karar maliyeti saniyelere iner.
- **Ölçüt:** Liste sıralı ve üst-sınırlı; her satır gerekçesini taşır; gerçek kullanımda
  inceleme oranı (bakılan/üretilen) izlenir — düşerse liste fazla gürültülüdür.

### H4 — Köken izlenebilirliği: kirlenme olursa bulunup temizlenebilsin

- **Amaç:** Etiket, türetilen her bilgiye **provenance üzerinden taşınsın**; "bu bilgi
  şüpheli/tek kaynaktan geldi" sorusu kalıcı olarak cevaplanabilsin.
- **Neden:** Blok olmadığı için kirlenme mümkündür (bilinçli takas, §9). Takasın
  savunulabilir olmasının tek şartı, kirlenmenin **geri alınabilir** olmasıdır. KASA'nın
  provenance zinciri bunu zaten mümkün kılıyor; kullanılmıyordu.
- **Ölçüt:** Bir kaynak kirli ilan edildiğinde ondan türeyen tüm profil girdileri tek
  işlemle listelenip yeniden etiketlenebiliyor (§6.5).

### H5 — Her eşiğin kanıtla sabitlenmesi

- **Amaç:** Hiçbir eşik "makul göründüğü için" seçilmesin; ölçülen yaygınlık ve maliyet
  asimetrisinden türetilsin.
- **Neden:** v1'in "yanlış-pozitif ≤ %2" hedefi taban oranı olmadan anlamsızdı ve
  ölçüldüğünde %4 kesinlik veriyordu (§7). Eşiksiz kod, kalibre edilemeyen koddur.
- **Ölçüt:** F0 tamamlanmadan F1 kodu yazılmaz. Her eşiğin yanında ölçüm kaydı bulunur.

### H6 — Dürüst kapsam beyanı: değerlendirilemeyen sessizce geçmesin

- **Amaç:** Sistemin değerlendiremediği içerik (desteklenmeyen dil, çözülemeyen biçim)
  "temiz" muamelesi görmesin; **`unassessed` etiketiyle** görünür olsun.
- **Neden:** Sessiz geçiş, kullanıcıya korunduğu yanılgısını verir — korumamaktan daha
  kötüdür. Ayrıca ücretli dil paketi kararının (§8) etik temeli budur: satılan şey
  koruma değil **kapsam**; temel ürün ne yapamadığını söyler.
- **Ölçüt:** Desteklenmeyen dilde içerik enjekte edildiğinde etiketsiz geçmediği test edilir.

### H7 — Ticari paketlenebilirlik, marka vaadini bozmadan

- **Amaç:** Dil kapsamı ücretli modül olarak paketlenebilsin; ama yerel-öncelikli /
  ağ-bağımsız vaat zedelenmesin.
- **Neden:** Her ek dilin marjinal maliyeti gerçek ve süreklidir (kalıp + negatif korpus +
  kalibrasyon + düşmanca tazeleme). Lisans sunucusu/telemetri ile gating yapılırsa
  ürünün temel iddiası çöker.
- **Ölçüt:** Paket, imzalı veri parçası olarak yerel doğrulanır; hiçbir ağ çağrısı yok.

## 2. Tehdit sınıfları

- **Sınıf 1 — Ajana yönelik direktif (enjeksiyon).** Muhatabı model/ajan olan talimat.
  Nadir, etkisi yüksek.
- **Sınıf 2 — İnsana yönelik manipülasyon.** Dolandırıcılık/reklam metni. Ajan
  kandırılmaz, sadakatle *aktarır*; zarar yayın anında doğar.
- **Sınıf 3 — Hakikate kayıtsız içerik.** SEO çiftliği, üretilmiş dolgu. Düşmanca değil,
  en yaygın kirletici. **Tespitle çözülmez**, yalnız gerekçe sınaması ve doğrulamayla
  seyreltilir.

## 3. Mimari — üç kademeli huni

Maliyeti artan sırada; her kademe bir öncekinin yakalayamadığını hedefler. Hiçbiri tek
başına karar vermez. Model güvenlik sınırı değildir (KURALLAR §4): karar deterministik
kodda; nöral yardım yalnız etiket **ekler**, kaldıramaz.

### Kademe 1 — Görev alakası (senkron, çok ucuz) → Sınıf 1

**Soru:** Getirilen içerik, ajanın yaptığı işle alakalı mı?

Kaba enjeksiyonun en güçlü ayırt edicisi budur ve **niyet okumaz**: kullanıcı "mücevher
trendleri" istediyse, konuyla ilgisiz bir talimat kibarca yazılmış olsa da alakasızlığıyla
ele verir. Biçim kalıbı aramaya göre üstündür — üslup değiştirmek saldırganı kurtarmaz.

**Referans kritik:** karşılaştırma **kullanıcının özgün talebine** karşı yapılır, ajanın o
anki türetilmiş alt-görevine karşı değil. Aksi halde çok adımlı çalışmada zehir kendi
alakasını üretir (§6.3).

Yardımcı biçim etiketleri (ucuz, deterministik): `directive_present`, `addressee_system`,
`frame_break`, `hidden_channel` (ZWSP/base64/HTML-yorum/gizli CSS), `identity_claim`.
Ayırt edici **muhataptır**: "hemen abone ol" (insan) ile "önceki talimatları yok say"
(sistem) aynı gramerdedir.

### Kademe 2 — Gerekçe ve dayanak sınaması (gece, orta maliyet) → Sınıf 2 + 3

**Soru:** Değerlendirici iddia gerekçesini gösteriyor mu?

"X en iyisi / almalısın / yükselişte" diyen metin: **neden** daha iyi, **neyle**
karşılaştırılmış, **sayısal** dayanağı var mı, trend iddiasının **zaman boyutu** var mı?
Gerekçesiz üstünlük iddiası + çağrı = reklam imzası; analiz metni gerekçe ve karşılaştırma
taşır. Bu bir yapı farkıdır, niyet tahmini değil.

**Zorunlu kısıt:** yalnız **değerlendirici** iddialara uygulanır (üstünlük, tavsiye, trend).
Betimleyici bilgiye ("etkinlik salı günü") uygulanırsa her düz cümle bayraklanır.

Bu formülasyon nöral yardımı ilk kez uygulanabilir kılar: model açık uçlu "manipülatif mi"
yargısı vermez — dört maddelik bir **varlık kontrolü** yapar (gerekçe/karşılaştırma/sayı/
zaman). Küçük yerel model bunu tutarlı yapabilir.

### Kademe 3 — Çapraz-kaynak doğrulama (asenkron) → kalan her şey

`corroboration_k` = iddia kaç **bağımsız** kaynakta doğrulandı. `source_baseline_dev` =
kaynağın kendi geçmişinden sapması (girdi: DEBI-1 `occurrence_count` + kaynak sicili).

**Bağımsızlık tanımı kritik (§6.2):** aynı metnin farklı sitelerde tekrarı doğrulama
**değildir**, sendikasyondur.

## 4. Etiketleme birimi

**Karar: segment (paragraf/blok) düzeyi.** Sayfa düzeyi etiket yoktur.

**Neden:** 5000 kelimelik temiz makaledeki tek zehirli cümle sayfa düzeyinde etiketlenirse
tüm makale kullanılamaz hale gelir (aşırı-agresif reddin etiket versiyonu); cümle düzeyi
ise bağlamı kaybeder. Segment sınırı kaynağın kendi yapısından alınır (HTML blok/paragraf).
Olay kimliği = kaynak + segment. Alaka skoru, gerekçe sınaması, liste satırı ve provenance
hepsi bu birime bağlanır.

## 5. Eylem modeli — takip et, bloklama

| Nokta | Davranış |
|-------|----------|
| **Alım** | Her içerik kaydedilir, etiketlenir. Reddetme/karantina/gizleme **yok**. |
| **Damıtma (kalıcı bilgiye terfi)** | Etiketli ∧ doğrulanmamış içerik kalıcı profile **terfi ettirilmez**; olay yerinde durur, "aday" kalır, doğrulama gelirse terfi eder. Blok değil, **bekletme** — veri silinmez, gizlenmez, sorgulanabilir. |
| **Okuma / yayın** | Etiketli kökenli her şey **işaretli** döner; yayın öncesi insan onayı bu işarete bakar. |

Bu, KASA'nın mevcut *read-through-redact* deseninin kardeşidir: müdahale yazma anında
değil, kullanım anında.

### 5.1 İnceleme listesi (H3'ün karşılığı)

Gün sonu özeti — mevcut gece damıtma işiyle (02:00) aynı çalıştırmanın yan ürünü, yeni
altyapı gerekmez. Uygulama içinden istendiği zaman da erişilebilir.

Satır alanları: **tarih · içerik özeti · kaynak · hedef · amaç-hipotezi · eksik kanıt ·
doğrulama durumu**.

**Amaç/niyet notu bir hipotezdir, tespit değildir** — makine kararı olarak kullanılmaz,
yalnız insan okuması için yazılır ve hipotez olarak işaretlenir. (Metinden niyet okunamaz;
ama insana sunulan bir okuma kolaylığı meşrudur.)

Kaynak sicili ayrı yüzey: bir alan adı sürekli `addressee_system` üretiyorsa bu, tekil
metni bayraklamaktan daha değerli sinyaldir — ve ancak hiçbir şey atılmazsa oluşur.

## 6. Bilinen açıklar ve kapatma kararları

Tasarımın kendi zayıflıkları; her biri için karar verildi.

**6.1 Etiketleme birimi belirsizdi** → §4'te segment düzeyi olarak sabitlendi.

**6.2 Sendikasyon, doğrulama sanılıyordu — en ağır açık.** Kademe 3 "kaç kaynakta geçiyor"
sayıyordu; içerik çiftlikleri aynı metni onlarca siteye kopyalar ve sayaç bunu
*doğrulanmış* sayardı. Savunma, saldırganın en ucuz hamlesiyle (kopyala-yapıştır) ters
yöne çalışırdı. **Karar:** bağımsızlık = köken farkı **ve** metin farkı. DEBI-1
`content_hash` + yakın-kopya benzerliği ile ölçülür; aynı/benzer metin doğrulama ağırlığını
**artırmaz, azaltır**.

**6.3 Alaka filtresi kendini zehirleyebilirdi.** Çok adımlı çalışmada ikinci adımın görev
bağlamı, birinci adımda gelen (belki zehirli) içerikten türer; zehir kendi alakasını
üretir. **Karar:** karşılaştırma daima **özgün kullanıcı talebine** karşı. `task_context`
alanı `{original_request_id, derived_subtask}` taşır; skor `original_request` üzerinden
hesaplanır.

**6.4 İnsan kararı kaydedilmiyordu.** Liste üretiliyor, insan "zehir/temiz" diyor, bilgi
buharlaşıyordu. **Karar:** inceleme kararı kaydedilir ve **kalibrasyon korpusunu besler**
— F0'da elle etiketlenen korpusun sürekli ve bedava devamı budur. Hangi bayrağın işe
yaramadığı da böyle ölçülür.

**6.5 Geriye dönük iptal yolu yoktu.** **Karar:** `source_revoke` işlemi — bir kaynak kirli
ilan edildiğinde provenance üzerinden ondan türeyen her şey listelenir ve yeniden
etiketlenir; gerekirse `forget`/`supersedes` ile temizlenir.

**6.6 İnceleme listesi dikkat-taşırma saldırısına açıktı.** Saldırgan orta-şüpheli içerik
basarak gerçek maddeyi ilk 10'un dışına düşürebilirdi. DEBI-0 yazma debisini sınırlıyordu
ama **dikkat debisi** sınırsızdı. **Karar:** günlük listede kaynak-başına kota; tek kaynak
listenin belirli oranından fazlasını işgal edemez.

**6.7 Dil kapsamı belirsizdi** → §8'de modül + `unassessed` etiketi olarak çözüldü.

**6.8 İstatistiksel iyimserlik.** "İki zayıf sinyalin çarpımı kesinliği yükseltir" savı,
sinyallerin **koşullu bağımsız** olduğunu varsayıyor; oysa gerekçesizlik ile
doğrulanmamışlık birlikte gider (çöp içerik ikisinden de yoksundur). **Karar:** bağımsızlık
bir **varsayımdır**, veri değildir; F0'da korelasyon ölçülür ve kesinlik tahmini ona göre
düzeltilir.

## 7. Ölçüm — mühür = ölçüm

### F0 zorunlu: yaygınlık önce ölçülür

> 10.000 paragraf, gerçek yaygınlık %0.1 (10 zehirli). Duyarlılık %90 → 9 yakalama.
> Yanlış-pozitif %2 → 9.990 × 0,02 ≈ **200 yanlış alarm**. Kesinlik ≈ **%4**.

Aynı taban oranında %50 kesinlik için yanlış-pozitifin **%0,09** olması gerekir — tek
kademeli zayıf bir ipucu detektörünün ulaşamayacağı değer. Huninin gerekçesi budur.
Eylem "etiket + bekletme" olduğu için düşük kesinliğin bedeli düşüktür; yine de ölçüm
zorunludur, çünkü **etiket enflasyonu** ("her şey şüpheli") sinyali öldürür (H3).

### Protokol

- **Yaygınlık (π):** gerçek tarama korpusundan örneklem + elle etiketleme; sonra §6.4
  geri besleme döngüsüyle sürekli güncellenir.
- **Metrikler:** ölçülen π'de kesinlik/duyarlılık, ROC-AUC, d′. Tek başına yanlış-pozitif
  oranı raporlanmaz (yanıltıcı).
- **Eşik:** beklenen maliyet minimizasyonu — C_kaçırma (zehirli iddia kalıcı profile
  terfi etti) vs C_yanlış-etiket (temiz bilgi doğrulama bekledi).
- **Negatif kontrol korpusu zorunlu:** temiz haber/blog **ve meşru pazarlama metni**
  (Kademe 2'de doğal yüksek skor — yanlış-pozitif kanamasının çıkacağı yer).
- **Düşmanca tazeleme:** yayımlanan kural listesi hedefe dönüşür (Goodhart); korpus
  periyodik yeniden üretilir, kalibrasyon kanıtı saklanır (`_orch/redteam/` deseni).
- **Testler** (`tests/test_ingest_label.py`): muhatap ayrımı, değerlendirici/betimleyici
  ayrımı, yanlış-pozitif kontrolü, redact-sonrası sıra, provenance'a taşınma, nöral
  kademenin etiket **silemediği**, sendikasyonun doğrulama sayılmadığı, ve **hiçbir yolun
  içerik silmediği/reddetmediği**.

## 8. Dil kapsamı ve paketleme

**Dile bağımlı olan, tasarımın zayıf kısımlarıdır.** Kademe 1'in kalıp etiketleri ve
Kademe 2'nin ikna/gerekçe sözlüğü dile bağlıdır. Buna karşılık **görev alakası** (çok
dilli gömme) ve **çapraz-kaynak doğrulama** (köken + metin benzerliği) büyük ölçüde
dilden bağımsızdır.

**Sonuç:** dil paketi olmayan kullanıcı savunmasız değildir — huninin en güçlü iki
kademesi çalışır, yalnız ipucu katmanları kapsam dışıdır. Satılan şey koruma değil,
o dilde **kesinlik**.

- **Temel pakette zorunlu (H6):** dil tespiti her zaman çalışır; desteklenmeyen dil
  `unassessed` etiketiyle görünür olur. Sessiz geçiş yasaktır.
- **Paketin içeriği:** asıl değer kalıp listesi değil — kopyalanabilir. Değerli olan
  **kalibrasyon kanıtı**: o dilde ölçülmüş yaygınlık, ölçülmüş yanlış-pozitif, negatif
  kontrol korpusu, eşiklerin hangi maliyet asimetrisiyle seçildiği.
- **Dağıtım (H7):** kod yolu kilitlenmez; **imzalı veri parçası** dağıtılır ve yerel
  doğrulanır. Lisans sunucusu, telemetri, eve-telefon yok.
- **Yükümlülük:** paket satmak, o dilin düşmanca tazelenmesini de satmaktır; tazeleme
  durursa paket değersizleşir.

## 9. Dürüst sınırlar

- Bu katman **niyet tespit etmez**; biçim etiketler, köken izler. İddia "tespit" değil,
  **"etiketleme + izlenebilirlik"**tir.
- **Blok olmadığı için** zehirli içerik damıtma bağlamına girebilir; kalıcı profil
  bekletmeyle korunur ama tek bir çalıştırmanın çıktısı etkilenebilir. Bilinçli takas:
  veri kaybetmemek için etkiyi izlenebilir kılmayı seçiyoruz (H2 + H4).
- İçerik çiftlikleri makul görünen gerekçe ve uydurma sayı üretebilir; Kademe 2
  saldırganın maliyetini yükseltir, kapıyı kapatmaz.
- Sockpuppet ağıyla **farklı metinlerle** aynı iddiayı yayan saldırgan Kademe 3'ü de geçer.
- Sınıf 3 çözülmez, yalnız seyreltilir.

## 10. Fazlar

| Faz | Kapsam | Ön koşul |
|-----|--------|----------|
| **F0** | Yaygınlık + korelasyon ölçümü, pozitif/negatif korpus (`docs/INJECTION_CORPUS.md`) | — |
| F1 | `ingest_label.py` Kademe 1 + `task_context` alanı + segment birimi + şema migration + testler | F0 |
| F2 | İnceleme listesi + kaynak sicili + kaynak kotası + inceleme kararı geri beslemesi | F1 mührü |
| F3 | Kademe 2 gerekçe sınaması (gece, idle/GPU kapılı) | F2 mührü |
| F4 | Kademe 3 çapraz-kaynak + sendikasyon ayrımı + `source_revoke` | F3 mührü |
| F5 | Dil paketi altyapısı (imzalı paket + `unassessed` yolu) | F3 |

Not: v1'de F1 kod yazmakla başlıyordu; v2'den beri **ölçüm önce gelir**.

## 11. Açık sorular (sahip kararı)

1. `ingest_labels` plaintext kolonu onaylı mı? (Yalnız kategori + skor; içerik taşımaz.)
2. Maliyet asimetrisi: bir kaçırılan zehir kaç gereksiz doğrulama-bekletmesine bedel?
3. "Bağımsız köken" için alan adı farkı yeterli mi, alan-sahipliği/ağ bloğu ayrımı da
   aransın mı? (Sockpuppet direnci buradan gelir.)
4. Terfi bekleyen aday olaylar TTL dolunca düşsün mü, süresiz mi beklesin?
5. Günlük listede kaynak-başına kota oranı ne olsun?
6. Temel pakette hangi diller yer alsın (TR + EN varsayılıyor)?
