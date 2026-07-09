# Proje KASA

Windows'ta Ajan Tabanlı Tarama için Egemen, Yerel-Öncelikli bir Hafıza Kasası

## Sorun

Bugünkü ajan tabanlı tarayıcılar, kalıcı kullanıcı hafızasını satıcı bulutlarında saklıyor; bu da ciddi gizlilik ve kontrol sorunları doğuruyor. Kullanıcılar tarama verilerine sahip olamıyor ve yapay zekâ ajanlarına izin vermenin yasal sonuçları net biçimde tanımlanmış değil. Bu proje, herhangi bir ajanın izin-aracılı bir MCP (Model Context Protocol) sunucusu üzerinden erişebileceği; yerel-öncelikli, şifreli ve kullanıcıya ait bir hafıza kasası sağlayarak bu eksiklikleri gidermeyi amaçlıyor.

## KASA Ne Yapar

KASA, Windows kullanıcıları için egemen bir hafıza kasası olarak tasarlanmıştır ve tarama verileri üzerinde tam kontrol sağlar. "Ajanlar gelip gider; hafızanız sizindir" ilkesine dayanır. Sistem şunları içerir:

- Tüm kullanıcı verisini şifreli biçimde yerelde saklayan bir Hafıza Kasası.
- Bu kasayı, aracılı bir protokol üzerinden izin sahibi her ajana açan bir MCP Sunucusu.
- Yalnızca yetkili ajanların veriye erişmesini sağlayan, kullanıcı bilgisi üzerinde sıkı denetim kuran bir izin hesabı (permission calculus).

## Mimari

KASA'nın mimarisi beş ana bileşenden oluşur:

| Bileşen | Rol | MVP Durumu |
|---------|-----|------------|
| Hafıza Kasası | Kullanıcı verisi için şifreli yerel depo | ✅ |
| MCP Sunucusu | Kasayı ajanlara açan localhost sunucusu | ✅ |
| Ajan Çekirdeği | Yerel model ve planlayıcı | ✅ (yalnızca damıtma) |
| İzin Aracısı | Dış erişim için deterministik geçit | ✅ (kapsam denetimleri) |
| Tarayıcı Uzantısı | Sayfaları okur, ileride eylem yürütür | Ertelendi |

### Tasarım Değişmezleri

1. **İnce Kenarlar, Kalın Çekirdek**: Uzantı hiçbir zekâ ve veri içermemeli; tüm durum yardımcı uygulamada tutulur.
2. **Model Güvenlik Sınırı Değildir**: Yetkilendirme kararları, sıradan kod içindeki İzin Aracısı tarafından verilir.
3. **Sayfa İçeriği Veridir, Komut Değildir**: Web'den gelen her metin alıntı verisi olarak etiketlenir. Hedefler yalnızca kullanıcının kendi komutlarından türetilebilir.

## Güvenlik

KASA güvenliği birçok önlemle önceliklendirir:

- **Kırmızı Takım Hikâyesi**: Proje, açıkları bulmak ve gidermek için titiz testlerden geçti. Başlıca bulgular ve alınan önlemler:
  - Gecelik damıtma zincirine yapılan komut enjeksiyonu; tüm güvenilmeyen olay metnini açık işaretçilerle sarıp bir QC köken (provenance) geçidi uygulanarak kapatıldı.
  - MCP yetkilendirme açıkları; ajanlar ve araçlar için sıkı izin-listeleri ve red-listeleri ile kapatıldı.
  - Otonom, sıfır-maliyetli test→düzelt döngüleri, gerçek tarayıcı sağlık kontrolleriyle sürekli güvenlik iyileştirmesi sağladı.

## Kurulum ve Çalıştırma

KASA'yı Windows'ta kurmak ve çalıştırmak için:

1. **Bağımlılıklar**: Gerekli Python paketlerini şu komutla yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
2. **Yerel Ollama Çalışma Zamanı**: `qwen2.5:7b` modeli yüklü, http://localhost:11434 adresinde çalışan bir yerel Ollama örneğinizin olduğundan emin olun.
3. **Yapılandırma**: `kasa.toml.example` dosyasını `kasa.toml` olarak kopyalayın ve sunucu host/port, kasa yolu gibi ayarları isteğinize göre düzenleyin.
4. **Sistem Tepsisi Uygulamasını Başlatma**: Uygulamayı şu komutla çalıştırın:
   ```bash
   python run.py
   ```
5. **Yalnızca MCP Sunucusu (Tepsisiz Mod)**: Tepsi simgesi olmadan yalnızca MCP sunucusunu çalıştırmak için:
   ```bash
   python run.py --no-tray
   ```
6. **Tek Bir Damıtma Turu Çalıştır ve Çık**: Tek bir damıtma turu çalıştırıp çıkmak için:
   ```bash
   python run.py --distill-now
   ```
7. **Şifreli Taşınabilir Dışa Aktarım**: Kasanızı şifreli bir dosya olarak dışa aktarmak için:
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

- MVP-0 güvenlik çekirdeği (kasa + MCP sunucusu + aracılı izinler + damıtma + denetim hash-zinciri) uygulandı ve güvenlik-sertleştirmesi yapıldı: tüm güvenlik testleri yeşil (komut enjeksiyonu, MCP yetkilendirme C5/C7/C8, tarayıcı sağlık geçidi). Dürüst çerçeve: komut enjeksiyonu tüm sektörde hâlâ açık bir problem sınıfıdır; KASA'nın savunması *yapısaldır* (model asla güvenlik sınırı değildir), bir dokunulmazlık iddiası değil.
- Tarayıcı uzantısı, web eylemleri (A1-A3), bulut maskeleme/yükseltme ve parmak izi sahteleme katmanı ertelendi / park edildi (MVP-0 kapsamı dışında).

## Lisans

Lisans: TBD
