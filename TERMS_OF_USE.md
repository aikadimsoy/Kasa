# KASA — Kullanım Şartları

**Sürüm 1.0** · Yürürlük: 2026-07-10

KASA'yı ("Yazılım") kullanmadan önce bu şartları okuyun. Yazılımı kurarak veya kullanarak
aşağıdaki şartları kabul etmiş olursunuz. Kabul etmiyorsanız Yazılımı kullanmayın.

---

## 1. Yazılımın Niteliği
KASA, kişisel hafıza/kayıt "kasası" olarak çalışan **yerel-öncelikli (local-first)** bir masaüstü
uygulamasıdır. Tüm işlevi kendi bilgisayarınızda çalışır.

## 2. Gizlilik ve Veri
- KASA yalnızca **127.0.0.1 (yerel makine)** üzerinde çalışır; verilerinizi bir sunucuya, buluta
  veya üçüncü tarafa **göndermez**.
- **Telemetri yoktur.** KASA sizi izlemez, kullanım verisi toplamaz.
- Verileriniz cihazınızda kalır. Yedekleme, taşıma ve silme sizin sorumluluğunuzdadır.

## 3. Güvenlik — Dürüst Beyan
- KASA, kayıtlarınızdaki hassas dizeleri (sırlar, anahtarlar vb.) **maskeleme (redaction)** ve
  hücre düzeyinde **AES-GCM şifreleme** ile korumaya çalışır.
- Şifreleme anahtarı, Windows **DPAPI** ile kullanıcı hesabınıza bağlıdır. Sır **kaynak kodda
  değildir**; dolayısıyla güvenlik kaynak gizliliğine dayanmaz (Kerckhoffs ilkesi).
- **Aşırı iddia yoktur:** KASA kendini "askeri düzey", "kurumsal düzey" veya "kırılamaz" olarak
  **tanımlamaz**. Tam-veritabanı disk şifrelemesi kademelidir; bazı bölümler beklemededir ve arayüz
  bunu dürüstçe belirtir. Güvenlik, ölçülene kadar mühürlenmez.
- Yazılım "**OLDUĞU GİBİ**" (as-is) sağlanır; belirli bir amaca uygunluk dâhil hiçbir garanti
  verilmez. Veri kaybı, ihlal veya zarardan geliştirici sorumlu tutulamaz.

## 4. Sorumluluğunuz
- Bilgisayarınızın ve kullanıcı hesabınızın güvenliği sizin sorumluluğunuzdadır (DPAPI anahtarı
  hesabınıza bağlıdır; hesabınız ele geçerse veriniz risk altındadır).
- KASA'yı yürürlükteki yasalara uygun ve yalnızca kendi verileriniz için kullanın.

## 5. Gelişmiş (Kilitli) Kademe
Bazı agresif özellikler **sahip-korumalı (owner-gated)**, şifreyle kilitli bir panel arkasındadır.
Bu özellikleri etkinleştirmek ve sonuçları sizin sorumluluğunuzdadır.

## 6. Üçüncü Taraf Bileşenler
KASA çalışmak için Microsoft **WebView2 Runtime** ve **Visual C++ Redistributable** bileşenlerine
ihtiyaç duyabilir. Bunlar Microsoft'a aittir ve kendi lisans şartlarına tabidir. KASA bunların
eksik olup olmadığını **yerel olarak** tespit eder ve eksikse resmi Microsoft indirme bağlantısını
açmayı önerir; sizin onayınız olmadan indirme/kurulum yapmaz.

## 7. Değişiklikler
Bu şartlar güncellenebilir. Sürüm numarası değişirse, güncel şartlar bir sonraki açılışta yeniden
gösterilir ve kabulünüz istenir.

---

*Bu belge hukuki danışmanlık değildir; yazılımın kullanım koşullarını sade dille açıklar.*
