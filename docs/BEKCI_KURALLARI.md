# Bekçi Kuralları — Canlı Bekçi (Guardian) Yapı ve Kural Taslağı

**Belge türü:** Mimari + yönetişim önerisi (canlı bekçi katmanı için)
**Durum:** 🟡 TASLAK / ÖNERİ — proje sahibi onayı bekliyor (KURALLAR.md Kural 1 & 3 gereği bu belge onaylanana kadar `KURALLAR.md`'ye ve `PROJECT_BRIEF.md`'ye DOKUNULMAZ).
**Bağlam:** Nihai vizyon "Agentic Browsing" (PROJECT_BRIEF başlığı) — tarayıcıya bağlı yerel AI'ın *canlı bekçi* olması. Bu belge o katmanın **güvenli çekirdeğini** (gözleyen/uyaran) ve sert sınırlarını tanımlar; riskli eylem katmanını (A1-A3) tanımlamaz — o hâlâ ertelenmiştir.

---

## 0. Neden yeni bir eksen?

Mevcut mimaride iki özerklik ekseni var:

- **T0–T3** = *eylem özerkliği* (ajan ne kadar serbest eylem yapar; PROJECT_BRIEF §7).
- **A0–A3** = *eylem sınıfı* (eylemin tehlike düzeyi; PROJECT_BRIEF §6.3).

Canlı bekçi bir **eylemci değil, bir duyu organıdır** (gözler + uyarı sesi). Onu T/A ekseninde tanımlamak yanlış olur — çünkü onun tehlikesi "ne yaptığı" değil, "ne gördüğü ve gördüğüne kanıp kanmadığı"dır. Bu yüzden üçüncü bir eksen öneriyorum:

- **G0–G3** = *bekçi özerkliği* (gözlem → uyarı → öneri → otonom müdahale).

Bekçi, T ve A eksenlerini **geçemez**: bir G-katmanı, karşılığı gelmeden T/A yetkisi kazandırmaz. Bekçi G1'de uyarı verse bile eylem T0'da (yalnızca öneri) kalır.

---

## 1. Bekçi Katmanları (G0–G3)

| Katman | Ad | Ne yapar | Ne YAPAMAZ | Durum |
|--------|-----|----------|------------|-------|
| **G0** | Pasif gözlem | Sayfa içeriğini **veri olarak** okur (Değişmez 3). Hiçbir çıktı üretmez, sorulmadıkça susar. Saf sensör. | Yazmaz, uyarmaz, hafızaya işlemez, eyleme dokunmaz. | ✅ Hedef (çekirdek) |
| **G1** | Uyaran bekçi | Risk kalıbı tespit eder (tracker, phishing, Cloudflare challenge, veri-sızdıran form, sayfa metnindeki komut-enjeksiyonu denemesi) ve kullanıcıya **uyarı yüzeyi** gösterir. | Kullanıcı yerine eylem yapmaz. Sadece "gördüm, dikkat" der. | ✅ Hedef (ilk canlı sürüm) |
| **G2** | Öneren bekçi | Uyarının ötesinde somut çözüm **önerir** ("bu challenge için Tracking Prevention'ı Basic yapayım mı?") — ama kullanıcı ONAYLAMADAN çalışmaz. | Onaysız hiçbir çözümü uygulamaz. | 🔒 Ertelendi (A1 + T1 ile eşleşir) |
| **G3** | Otonom bekçi | İzin-listesindeki kalıplarda sormadan müdahale eder. | — (bu, brief'in %90 risk diye bilinçle ertelediği katman) | 🔒 Ertelendi (A2-A3 + T2-T3) |

**Sert sınır (şu an geçerli):** Yalnızca **G0 ve G1**. G2 ve üstü, zemin yayınlanıp ilk kullanıcı/geri-bildirim gelene VE bu belge onaylanana kadar kilitli. Bekçinin kodunda G2+ için hiçbir "sap" (action handle) bulunmaz — ertelenmiş katman *kapsamda değil*, sadece *tasarımda öngörülmüş*tür (brief §6.3 deseni).

---

## 2. Bekçi Değişmezleri (Design Invariants 4–6 önerisi)

PROJECT_BRIEF §4'teki 3 değişmezi **iptal etmez, genişletir**. Bekçi en yüksek değerli komut-enjeksiyonu hedefidir; bu üç kural onu izole eder.

**Değişmez 4 — Bekçi gözler, eylemez.**
Sahip G1'in ötesine terfi ettirmeden, bekçinin eyleme, DOM'a, ağa veya izin aracısının *grant* yoluna **hiçbir tutamağı yoktur**. Yalnızca kullanıcıya uyarı/işaret yayar. Bu, modelin iyi niyetiyle değil, **kodda** zorlanır (bekçi süreci salt-okunur bir gözlem kanalına bağlıdır; yazma/eylem API'si erişiminde değildir).

**Değişmez 5 — Bekçinin gördüğü de veridir.**
Değişmez 3'ün bekçiye uygulanmışı. Bekçi bir sayfada "bana şunu yap" yazısı görse, bunu *bildirir* ("bu sayfa beni yönlendirmeye çalışıyor") ama **uyamaz**. Sayfanın algısı asla bekçinin hedefi olamaz. Canlı bekçi doğrudan enjeksiyon hattında durduğu için bu kural pazarlık dışıdır.

**Değişmez 6 — Bekçi hafızayı kirletmez.**
Bekçinin gözlemleri kasadaki profile **otomatik yazılmaz**; geçici (ephemeral) uyarılardır. Hafızaya yalnızca mevcut damıtma yolu (provenance/QC kapısıyla, brief §8.3) yazar. Böylece zehirli bir sayfa, bekçi üzerinden profile sahte gerçek ekleyemez.

**(Değişmez 2 zaten geçerli:** bekçi model-güdümlü olduğundan asla güvenlik sınırı değildir; uyarıları tavsiyedir, broker her şeyi yine deterministik kodda kapılar.)

---

## 3. "Profil Yükseltme" — mimariye bekçinin oturması

Bekçi yeni bir bileşen icat etmez; **Agent Core (bileşen #3)** üzerine bir *alt-rol* olarak biner ve read-only uzantının (bileşen #5, V0.2'de "gözler") çıktısını tüketir.

| # | Bileşen | Bekçi ile ilişki |
|---|---------|------------------|
| 3 | Agent Core | Bekçi mantığı burada koşar (yerel model). G0/G1 = gözlem + risk-sınıflandırma; hafıza yazmaz. |
| 5 | Browser Extension | Bekçinin "gözü". V0.2 read-only ingestion, bekçiye salt-okunur sayfa akışı verir. |
| — | (yeni) Uyarı Yüzeyi | G1'in çıktısı: tray/overlay üzerinde ne-gördüm bildirimi. Eylem düğmesi YOK (Değişmez 4). |

**Roadmap yerleşimi (brief §8'e önerilen ek — sahip kararı):**
`V0.2 read-only uzantı → **V0.2.5 Bekçi G1 (uyarı katmanı)** → V0.3 bulut maskeleme → V0.4 eylem A1 (= Bekçi G2'nin açılabileceği ilk nokta)`.
Bekçi G1, V0.2'nin "gözleri" üzerine kurulan zekâdır; kendi başına yeni bir eylem yüzeyi açmaz, o yüzden V0.3'ten önce güvenle gelebilir.

---

## 4. "Katmanları Güçlendirme" — G1 öncesi sertleştirme kapısı

Canlı bekçi, enjeksiyon riskini yükseltir (model artık her sayfayı sürekli okur). Bu yüzden G1 CANLIYA ÇIKMADAN ÖNCE şu mevcut katmanlar kanıtlı-yeşil olmalı:

1. **Veri/komut ayrımı (Değişmez 3 + 5):** tüm sayfa metni `UNTRUSTED` işaretçileriyle sarılı; bekçi promptu hedefini asla sayfadan türetmiyor. → #17 deterministik kalkan testi (halihazırda 19/19 yeşil) bekçi promptunu da kapsayacak biçimde genişletilir.
2. **Hafıza-kirletme koruması (Değişmez 6):** bekçi çıktısının kasaya yazmadığını doğrulayan bir regresyon testi.
3. **Eylem-izolasyonu (Değişmez 4):** bekçi sürecinin eylem/DOM/grant API'sine tutamağı OLMADIĞINI doğrulayan bir test (sap sızarsa test kırmızı).
4. **Fingerprint park listesi (B1-B4):** bekçi bir gizlilik aracı olarak sunulacaksa, park edilmiş sızıntılar (WebGL/TZ/Accept-Language) bekçinin "seni koruyorum" iddiasını zayıflatır — G1 pazarlaması bunları ya kapatmalı ya da dürüstçe "henüz değil" demeli.

Bu dördü, bekçinin "güçlendirilmiş katmanları"dır: yeni özellik değil, **var olan savunmanın bekçiyi taşıyacak kadar sağlam olduğunun kanıtı**.

---

## 5. Sıra ve Onay Kapıları (governance)

1. **Bu belge onaylanır** (sahip: G1 sınırı, Değişmez 4-6, roadmap yeri kabul mü?). Onaysız `KURALLAR.md` güncellenmez.
2. Onay sonrası: Değişmez 4-6 `KURALLAR.md`'ye, roadmap notu `PROJECT_BRIEF.md` §8'e işlenir (Kural 3: her değişiklik izinle).
3. **Zemin yayını** (README + git init/push) — bekçiden ÖNCE. Bekçi, yayınlanmış+geri-bildirim almış çekirdeğin üstüne kurulur.
4. §4'teki 4 sertleştirme kapısı yeşil → **ancak o zaman** G1 kodlanır (sıfır-token: yerel modeller üretir, Claude iskele + doğrulama).
5. G2+ açılışı ayrı, açık bir sahip kararıdır — bu belge onu yetkilendirmez.

---

*Hazırlayan: Claude, mimari-öneri olarak. Tüm katman sınırları ve değişmezler ÖNERİDİR; G1 sert sınırı ve ertelenmiş G2+ kararı sahip onayına tabidir. Bu belge onaylanana kadar hiçbir onaylı belge değiştirilmez ve hiçbir bekçi kodu yazılmaz.*
