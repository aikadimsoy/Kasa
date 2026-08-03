# KASA — Kaynak Koruma Araştırma Notu

> Bu not **yerel model** (qwen2.5-coder:14b) tarafından üretildi (zero-token politikası; Claude yalnız orkestrasyon). Model bilgi-sentezidir, canlı web makalesi değildir. Karar/uygulama bağlamı: `docs/EXE_PACKAGING_LOG.md`.

---

# Teknik Araştırma Notu: Bir Windows .exe olarak Dağıtılan Python Uygulamasının Kaynak Kodunu Koruma

## 1. Tehdit: exe'den kaynak çıkarma

### PyInstaller nasıl çalışır?
PyInstaller, Python uygulamalarını tek bir yürütülebilir dosya (.exe) olarak paketlemek için kullanılır. Bu işlem iki ana bileşenden oluşur:
- **Bootloader**: Uygulamanın başlatılması ve yönetimi için gerekli olan temel kodlar.
- **Gömülü .pyc dosyaları**: Python kodları derlenmiş (.pyc) hale getirilir ve exe dosyasına gömülebilir.

### Pyinstxtractor ile açma
Pyinstxtractor, PyInstaller tarafından oluşturulan .exe dosyalarını açmak için kullanılır. Bu aracı kullanarak exe dosyası içindeki .pyc dosyalarını çıkarmak mümkündür.

### Decompyle3/uncompyle6/pycdc ile .pyc -> okunur .py geri-derleme
.pyc dosyalarını okunabilir .py dosyalarına dönüştürmek için decompile araçları kullanılabilir. Bu araçlar, PyInstaller tarafından oluşturulan exe dosyasındaki .pyc dosyalarını geri derleyerek orijinal Python kodlarını elde etmeye çalışır.

### Neden "exe = güvende" bir yanılgı
Exe dosyalarının kaynak kodunu koruması konusunda güvenilir olmayan bir düşünce, çünkü exe dosyası içindeki .pyc dosyalarını çıkarmak ve geri derlemek oldukça kolaydır. Bu nedenle, exe dosyalarının güvenliği sadece kaynak kodunun gizliliğine dayanmamalıdır.

## 2. Nuitka (en güçlü koruma)

### Python -> C -> native makine kodu
Nuitka, Python kodlarını doğrudan C diline çevirir ve ardından bu C kodlarını derleyerek yerel makine koduna dönüştürür. Bu işlem sonucunda .pyc dosyaları oluşmaz, çünkü kodlar doğrudan C'ye çevrilir.

### Sınırlar
- **String sabitleri/mantık izleri binary'de kalabilir**: Nuitka tarafından oluşturulan exe dosyasında bazı string sabitleri ve mantık izleri hala görünmektedir. Bu nedenle, deterministik tersine mühendislik yoluyla bazı bilgiler elde edilebilir.
- **Tersine mühendis yine analiz eder**: Nuitka tarafından oluşturulan exe dosyası, disassembly yöntemiyle incelemek mümkündür. Ancak, bu yöntem genellikle pratikte imkansızdır.

### Windows'ta C derleyici gerekir
Nuitka'nın çalışabilmesi için bir C derleyicisi gereklidir. Nuitka, MinGW64'ü otomatik olarak indirebilir ve kullanabilir.

## 3. Diğer katmanlar (defense in depth)

### PyArmor (bytecode şifreleme + runtime guard), obfuscation sınırları
PyArmor, Python bytecode'ını şifreler ve çalışma zamanında korur. Ancak, bu yöntem sadece bytecode düzeyinde koruma sağlar ve kodun tamamını okunabilir hale getirmeyi zorlaştırır.

### Docstring/comment stripping, sembol adı sadeleştirme
Docstring ve yorumları kaldırarak kodun okunabilirliğini azaltabilirsiniz. Ayrıca, sembol adlarını basit ve anlamsız hale getirerek kodun anlaşılırlığını düşürebilirsiniz.

### İkili sıkıştırma/paketleme (UPX) yalnız boyut, koruma DEĞİL
UPX (Ultimate Packer for eXecutables), exe dosyalarını sıkıştırarak boyutunu azaltır. Ancak, UPX sadece boyutu azaltır ve kodun güvenliğini artırmaz.

## 4. Kerckhoffs ilkesi (önemli)

### Bir sistemin GÜVENLİĞİ kaynak gizliliğine dayanmamalı
Kerckhoffs ilkesi, bir sistemin güvenliği sadece bilinçsiz kullanıcılara karşı korunmalıdır. Sır = anahtar (örneğin, Windows DPAPI ile korunan vault anahtarı), kod değil. Kaynak sızsa bile şifreli veri güvende kalmalıdır.

### Kaynak-koruma = fikri-mülkiyet (rekabet) meselesi, güvenlik açığı değil
Kaynak kodunun gizliliği, genellikle rekabet avantajı için kullanılır. Ancak, bu yöntem sadece fikri mülkiyet meselesidir ve güvenlik açığı değildir.

## 5. Gerçekçi beklenti

### Local-first bir uygulama mantığını istemciye taşır; %100 koruma imkansız
Local-first bir uygulama mantığı, tüm işlevselliği istemci cihazına taşıyarak sunucu-tarafı güvenliği sorunlarını azaltır. Ancak, %100 koruma imkansızdır. Hedef: çıtayı "sıradan kopyalama başarısız olacak" kadar yükseltmek.

### Nuitka bunu ciddi ölçüde sağlar
Nuitka, Python kodlarını doğrudan C'ye çevirerek exe dosyası oluşturur ve bu işlem sonucunda .pyc dosyaları oluşmaz. Bu nedenle, exe dosyasının güvenliği daha yüksek olabilir.

## 6. Öneri

### Nuitka + docstring strip; sırları koda gömme (anahtar DPAPI'de); lisans/yasal koruma; kritik sunucu-tarafı mantığı varsa istemciye taşıma
- **Nuitka**: Python kodlarını doğrudan C'ye çevirerek exe dosyası oluşturur ve bu işlem sonucunda .pyc dosyaları oluşmaz.
- **Docstring strip**: Docstring ve yorumları kaldırarak kodun okunabilirliğini azaltabilirsiniz.
- **Sırları koda gömme (anahtar DPAPI'de)**: Sırları koda gömerek, kodu daha güvenli hale getirebilirsiniz. Ancak, bu yöntem sadece fikri mülkiyet meselesidir ve güvenlik açığı değildir.
- **Lisans/yasal koruma**: Lisans ve yasal koruma mekanizmalarını kullanarak uygulamanın kullanımını kısıtlayabilirsiniz.
- **Kritik sunucu-tarafı mantığı varsa istemciye taşıma**: Kritik sunucu-tarafı mantığını istemciye taşıyarak, sunucu-tarafı güvenliği sorunlarını azaltabilirsiniz.
