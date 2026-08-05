# İş hattı / Work Pipeline — 2026-08-05

**Amaç:** hiçbir iş denetimsiz koşmasın, durum bağlamda değil **dosyada** dursun, her aşamanın
arıza planı olsun.
**Purpose:** nothing runs unsupervised, state lives in **files** not in context, every stage has a
failure plan.

---

## 0. Neden bu belge var / Why this exists

Bu oturumda üç ayrı arıza sınıfı yaşandı ve üçü de sessizdi:

| Yaşanan | Nasıl fark edildi | Ders |
|---|---|---|
| Delege edilen ajan API yüklenmesinden düştü (**3 kez**) | Bildirim geldi | Ajan güvenilir bir kanal değil; küçük iş delege edilmez |
| Test koşumu HTTP 405 aldı, profil boş kaldı → **savunma tutmuş gibi göründü** | `errors` alanı okundu | Boş sonuç, başarılı savunmadan ayırt edilemez |
| Ölçtüğüm dosya ölçüm sırasında **büyüdü** (commit `e3211ee`, +6 test) | Sayı tutmadı, git'e bakıldı | Ölçülen şey ölçülürken değişebilir |
| 12 ajanlık sentez "en değerli bulgunuz" dedi, **yanlış okumaydı** | Birincil kaynak açıldı | Sentez birincil kaynağın yerine geçmez |

Hepsinin ortak yanı: **sessiz başarısızlık.** Hiçbiri hata vermedi, hepsi başarı gibi göründü.

---

## 1. Durum panosu / State board

Her aşama şu dördü taşır: **önkoşul · eylem · başarı ölçütü · arıza planı**.

### AŞAMA 0 — Hijyen (yinelenen)

| | |
|---|---|
| **Önkoşul** | — |
| **Eylem** | Test portları (8000-8005) boş mu, `d:\kasa`'dan koşan artık süreç var mı |
| **Başarı** | Sıfır dinleyici, sıfır artık |
| **Arıza** | Varsa PID'i **komut satırıyla doğrula**, sahibininkiyse dokunma |
| **Durum** | ✅ 2026-08-05 temiz — 6 süreç var, hepsi sahibin (openclaw, streamlit×2, ComfyUI, uvicorn×2) |

Komut:
```powershell
foreach ($p in 8000..8005) { Get-NetTCPConnection -LocalPort $p -State Listen -EA SilentlyContinue }
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select ProcessId, CommandLine
```

---

### AŞAMA 1 — Koşulsuz ölçümler (4 iş, bağımsız)

Hiçbiri ajan cevabına bağlı değil. **Bunlar yapılmadan hiçbir sayı savunulamaz.**

| # | İş | Başarı ölçütü | Arıza planı |
|---|---|---|---|
| **B1** | 20/20'yi önceden var olan meşru hafızayla yeniden koş | Sayı ya ayakta kalır ya düşer; **ikisi de yayımlanabilir** | `errors` boş değilse **hüküm okunmaz** |
| **B2** | Notlamaya başka-sözcük (paraphrase) koşulu ekle | Kopyalama mı inanç mı olduğu ayrışır | İmleç enjekte metinde geçiyorsa test geçersiz |
| **B3** | İyi niyetli yazmaların geçiş oranını ölç | Çalışma noktası çıkar | Masum vaka seti yoksa önce o kurulur |
| **C1** | Yük çifti + tam kapı izini yayımlanabilir esere çevir | **Yabancı 10 dakikada tekrarlar** | Tekrarlanamıyorsa eser değil, anekdot |

**Her koşumda kaydedilecek:** git SHA, model etiketi, tarih, `errors` alanı, ham model çıktısı.
Bunlar olmadan ölçüm tekrar edilemez.

---

### AŞAMA 2 — Savunma değerlendirmesi (tıkalı)

| | |
|---|---|
| **Soru** | MemTxn'in Ordered PatchTest'i ve OWASP Agent Memory Guard **bizim yükümüzü** yakalıyor mu |
| **Önkoşul** | İki belgenin tam metni |
| **Durum** | 🔴 **TIKALI** — Fable 5 ajanı 3 kez API 529'dan düştü |
| **Arıza planı** | **Kendim okurum.** İki belge, delege etmeye değmez. Ajan denemesi en fazla 1 kez daha. |

**Neden önemli:** yakalıyorsa hamlemiz saldırmak değil, *yayımlanmış bir savunmayı yerel-öncelikli
zeminde 7-8B modellerle uygulayıp ölçmek* olur — bunu kimse yapmadı. **Yakalaması iyi haber.**

---

### AŞAMA 3 — Kayıt düzeltmesi (Aşama 1'den sonra)

Yayımladığımız arşiv, özgünlük denetiminin çürüttüğü iddialar taşıyor.

| Dosya | Düzeltilecek |
|---|---|
| `docs/KNOWLEDGE_ARCHIVE.md` | Fikir #11 → C2PA §7.2 ve Clark-Wilson'a atfedilmeli |
| `SECURITY.md` | F-POISON → alan bağlamı + "replikasyon + artım" çerçevesi |
| İkisi de | F-POISON'un öncel sanatı yokmuş gibi okunduğu her yer |

**Neden Aşama 1'den sonra:** sayılar kesinleşmeden metni iki kez yazmayalım.

---

### AŞAMA 4 — Sahip kararları (bloklayıcı)

| | Karar | Bağımlı olduğu |
|---|---|---|
| **A4** | r/mcp `p0xmazq` yorumu bizim mi? Bizse üçüncü taraf öncel sanat diye anılamaz | — **hâlâ cevapsız** |
| **D1** | Ad-uzayı atlatması: belgele / destek kontrolü uygula / karantina | Aşama 2 |
| **D2** | 6 commit push edilecek mi | — |
| **D3** | APAS yanıtını yeniden yaz | Aşama 2 + A4 |

---

## 2. Arıza sınıfları ve korumaları / Failure modes and guards

| Arıza | Belirti | Koruma |
|---|---|---|
| **Ajan API yüklenmesi** | 529 / "Overloaded" | En fazla 1 tekrar, sonra kendim yaparım. Küçük iş zaten delege edilmez. |
| **Sessiz yanlış-negatif** | Boş sonuç, `errors` dolu | **Kural: `errors` boş değilse hüküm YAZILMAZ.** Betik bunu kendi basar. |
| **Ölçülen şey değişiyor** | Sayı tutmuyor | Her ölçümle **git SHA** kaydedilir |
| **Sentez ≠ kaynak** | İkinci elden alıntı | **Yayımlanacak hiçbir alıntı özetleyiciden alınmaz** |
| **Gerçek vault'a bulaşma** | — | Test **daima** izole vault, `KASA_VAULT_PATH` ayrı dizin |
| **Artık süreç/sunucu** | Port dolu, CPU | Her testten sonra Aşama 0 |
| **Sahibin süreçlerine dokunma** | — | PID öldürmeden **komut satırı doğrulanır** |

---

## 3. Haberdarlık kuralları / Notification discipline

**Başlarken:** ne başlattığımı, neyi ölçtüğünü ve ne kadar süreceğini söylerim.
**Biterken:** sonucu ham hâliyle veririm — `errors` alanı dahil.
**Takılınca:** üç kez denemem. İkinci arızada durur, size söyler, alternatif öneririm.
**Beklerken:** boş beklemem; koşulsuz işlerden birini yaparım.

**Asla:** arka planda kendi kafasına iş bırakmam. Koşan her şeyin bu belgede bir satırı olur.

---

## 4. Şu anki durum / Current state

```
AŞAMA 0  ✅ temiz
AŞAMA 1  ⬜ başlanmadı — B1, B2, B3, C1 (koşulsuz, hemen başlanabilir)
AŞAMA 2  🔴 tıkalı — ajan 3 kez düştü, kendim okuyacağım
AŞAMA 3  ⬜ Aşama 1'i bekliyor
AŞAMA 4  ⏸ sahip kararı bekliyor (A4 cevapsız)
```

**Koşan iş:** yok.
**Push edilmemiş commit:** 6.

---

Yazar / Author: [@aikadimsoy](https://github.com/aikadimsoy)
