# KASA Masaüstü Exe — Paketleme Günlüğü (adım dosyası)

> **Bu dosya nedir:** paketleme çalışmasının mühendislik günlüğü — tarih sırasıyla hangi
> seçenek denendi, ne ölçüldü, hangi karar neden verildi. Referans belgesi değil, kayıt.
> Build reçetesinin ve "neden Python 3.12" kararının gerekçesi burada durur; `build_kasa.ps1`,
> `src/desktop/__init__.py` ve `src/desktop/launch.py` bu dosyaya atıf yapar.
>
> **Temizlik notu (2026-08-03):** public yayın öncesi makine ve kişiye özgü izlerden arındırıldı —
> mutlak yollar `<depo-koku>` ile genelleştirildi, oturuma özgü notlar çıkarıldı. Teknik içerik,
> ölçümler ve kararlar değiştirilmedi.

> Amaç: bağlam-sürekliliği. Her yeni oturumun BAŞINDA bu dosya okunur; en son durum,
> ne yapıldı, sıradaki adım buradan devralınır. Kısa + tarihli tut. Kanonik plan:
> `docs/UI_UX_STANDARD.md` (pano) + bu dosya (paketleme).

## Hedef
KASA'yı çift-tıkla açılan native masaüstü uygulaması yapmak (Google Chat/Cloud app gibi):
PyInstaller ile paketli exe → içinde Python + FastAPI server + pano. Kullanıcıda Python
GEREKMEZ. Electron/Tauri YOK (toolchain duvarı). Bootstrapper (Python kur) YOK (invazif/anti-air-gap).

## Mimari karar (onaylı)
- **Model C**: pywebview penceresi (WebView2) + pystray tray + uvicorn arka-thread; PyInstaller bundle.
- v1 kapsam: **vault + pano** (salt-okunur; Ollama GEREKMEZ). Distill = Ollama varsa runtime opsiyonel.
- Vault yolu (exe): `%APPDATA%\KASA\vault` (dev depo kökü ayrı kalır). [owner onayı bekliyor]

## Fizibilite (ölçüldü, 2026-07-10)
- Kurulu: pyinstaller 6.20, cx_Freeze 8.6, pywebview 6.2, pystray 0.19.5, pillow 12.2,
  cryptography 49, pywin32 311, pythonnet 3.1, fastapi 0.138, uvicorn 0.48.
- Python: 3.14 (aktif), 3.12, 3.11 mevcut → PyInstaller 3.14 tutmazsa 3.12 fallback.
- C derleyici duvarı YOK (packager mevcut wheel'leri gömer).

## Plan (fazlar)
- **Faz 0 — Spike (go/no-go):** uvicorn-in-thread + cryptography + pywebview/pystray FREEZE + çalışır mı? ← ŞU AN
- Faz 1 — Launcher `src/desktop/launch.py` (uvicorn bg-thread + pywebview + pystray; %APPDATA%\KASA).
- Faz 2 — PyInstaller `.spec` (one-folder → one-file; dashboard_ui/design_system/config veri gömme).
- Faz 3 — Cila: ikon/.ico, versiyon, WebView2 runtime kontrolü, kod imzalama (owner/cert), installer.

## Durum günlüğü
- **2026-07-10:** Plan onaylandı, yeşil ışık. Faz 0 spike başlatıldı. Adım dosyası oluşturuldu.
  - [x] Spike A: kaynak thread deseni (ThreadedUvicorn = signal-handler'sız `uvicorn.Server`, bg-thread) → **PASS** (py 3.14, SERVER_OK)
  - [x] Spike B: PyInstaller freeze headless → **SPIKE_PASS, exit 0** (FROZEN True, PYVER 3.14.5; uvicorn bg-thread serve + cryptography runtime + pywebview/pystray import hepsi frozen'da çalıştı)
  - [x] Spike C: pywebview penceresi + uvicorn bg-thread aynı process → kaynak **PASS** + **FROZEN PASS** (WINDOW_UP → WEBVIEW_RETURNED → SPIKE_C_PASS, exit 0; pencere gerçekten açıldı/kapandı)
  - [x] 3.14 fallback GEREKMEDİ — PyInstaller 6.20 Python 3.14'ü tutuyor

## ★ FAZ 0 SONUÇ: **GO (yeşil)** — yığın donuyor, hiçbir temel duvar yok
Kanıtlanan (ampirik, frozen exe koşuldu):
1. PyInstaller 6.20 + **Python 3.14** çalışıyor (fallback'e gerek yok).
2. **uvicorn arka-thread'de** (ThreadedUvicorn deseni) frozen'da serve ediyor.
3. **cryptography** (native) frozen exe içinde runtime'da iş görüyor.
4. **pywebview (WebView2) penceresi + uvicorn** aynı process'te; GUI ana-thread + worker-thread dansı frozen'da SORUNSUZ.
5. pystray frozen'da import oluyor (tray için hazır).

**Çözülen gotcha (Faz 2 .spec'e yazılacak):** ortamda **hem PyQt5 hem PyQt6** kurulu; pywebview'ın Qt backend'i ikisini de çekince PyInstaller "multiple Qt bindings" ile ABORT eder. Çözüm: `--exclude-module PyQt5/PyQt6/PySide2/PySide6` (+ tkinter) → pywebview WebView2 backend'e düşer. **Bu exclude'lar .spec'te ZORUNLU.**

**Bundle boyutu:** one-folder ~**132 MB** (pywebview+pythonnet+fastapi+cryptography). Kabul edilebilir (Electron 150-250MB); ileride slim edilebilir.

Spike dosyaları: `scratchpad/spike_server_thread.py`, `spike_webview.py` (+ dist/ build/) — tek-kullanımlıktı,
depoda tutulmadı (`scratchpad/` yok); burada yalnız kayıt olarak anılıyor.

## Faz 1 — Launcher: **TAMAM** (2026-07-10)
`src/desktop/launch.py` yazıldı + kaynak-smoke **PASS** (`exit 0`, `SELFTEST server_ready port=51674`).
ThreadedUvicorn(boş port) bg-thread → health poll → pywebview `/dashboard` → pystray tray → temiz kapanış.
Veri dizini `%APPDATA%\KASA` (vault + config, `setdefault` → dev override korunur). `server.py` artık
`KASA_CONFIG` env'ini onurlandırıyor (frozen'da yazılabilir config konumu). Çalıştır: `py -m src.desktop.launch`.

## ★ KAYNAK KORUMA (source protection) — kullanıcı isteği: "kaynak çalınmasın"
**Dürüst gerçek:** düz PyInstaller kaynağı KORUMAZ (`.pyc` gömer → `pyinstxtractor`+decompiler ~%90 geri çıkar).
**Kerckhoffs:** KASA'nın GÜVENLİĞİ kaynak gizliliğine BAĞLI DEĞİL — vault güvenliği = DPAPI anahtarı + AES-GCM,
kod değil. Kaynak sızsa bile vault güvende (saldırganda kullanıcının DPAPI anahtarı yok). Yani kaynak-koruma =
**IP/rekabet-moat** meselesi, güvenlik açığı değil. Local-first app doğası gereği mantığını client'a taşır → mutlak
koruma imkânsız; hedef = çıtayı yükseltmek.
**Ölçüm (2026-07-10):** Nuitka YOK, PyArmor YOK, **C derleyici YOK** (cl/gcc/clang), MSVC/MinGW yok. `zstandard` var.
**Seçenekler:** (A) **Nuitka** = C'ye derle (en güçlü; bytecode-decompile yolu kapanır, ikili tersine
mühendislik pahalılaşır — mutlak koruma değil); pip install + MinGW64 oto-indirme
(~200MB, internet, build-only) + Py3.14 doğrulaması ister. (B) **PyArmor** = bytecode şifrele+runtime-guard (derleyicisiz,
orta-güçlü; ücretsiz tier sınırlı). (C) düz PyInstaller = zayıf/çıkarılabilir (istenmiyor).
**KARAR BEKLİYOR** (owner): A vs B. Öneri: A (Nuitka) — ücretsiz/OSS + en güçlü; tek maliyet bir kerelik MinGW indirmesi.

## KARAR + KURULUM (2026-07-10)
- **Owner kararı: NUITKA** (en güçlü; kaynak korumaz misconception'ı düzeltildi, Kerckhoffs anlatıldı).
- **Nuitka 4.1.3 KURULDU** (`py -m nuitka --version` → Python 3.14.5 tanınıyor).
- **Kaynak-koruma araştırma notu** yerel model (qwen2.5-coder:14b) ile üretildi (zero-token) → `docs/SOURCE_PROTECTION_NOTES.md`.
- MinGW64 HENÜZ indirilmedi (ilk `--standalone` derlemede Nuitka oto-indirir, ~200MB).

## Nuitka'ya geçiş — planlanan adımlar (2026-07-10)
Bu adımlar Nuitka kararı alındıktan sonra, ölçüm yapılmadan ÖNCE yazıldı (aşağıdaki
"NUITKA YÜRÜTME" bölümü bunların gerçekte ne verdiğini kaydeder).

1. **Nuitka minimal spike** (MinGW fetch + 3.14 doğrula): küçük bir script'i `py -m nuitka --standalone --assume-yes-for-downloads --output-dir=<depo-koku>/build_nuitka <script>.py` ile derle, exe çalışıyor mu bak. MinGW ilk sefer ~200MB iner.
2. **Faz 2 — launcher'ı derle** (Qt-exclude ZORUNLU + veri gömme):
   `py -m nuitka --standalone --onefile --windows-console-mode=disable --nofollow-import-to=PyQt5,PyQt6,PySide2,PySide6,tkinter --include-package=src --include-data-dir=<depo-koku>/dashboard_ui=dashboard_ui --include-data-dir=<depo-koku>/design_system=design_system --assume-yes-for-downloads --output-dir=<depo-koku>/build_nuitka <depo-koku>/src/desktop/launch.py`
   (pywebview/uvicorn için gerekirse `--include-package=webview,uvicorn` + Nuitka pywebview desteği kontrol.)
3. Çıkan `launch.exe`'yi çalıştır → pencere `/dashboard` açılmalı; `KASA_VAULT_PATH=<depo-koku>` ile gerçek veri.
4. Çalışırsa: ikon/.ico + isim `KASA.exe` + Faz 3 (imza/installer).

### Bilinen riskler (spike'ta ölç)
- Nuitka + pywebview (WebView2/pythonnet .NET) veri/DLL toplama — Nuitka'nın pythonnet/clr desteği kontrol edilmeli.
- Nuitka + uvicorn dinamik import'lar (`--include-module` gerekebilir).
- Qt binding çakışması (PyInstaller'da oldu) — Nuitka'da `--nofollow-import-to` ile kesildi.
- 3.14 tam uyum (Nuitka 4.1.3) — minimal spike doğrulayacak.

## ★ NUITKA YÜRÜTME (2026-07-10) — ölçülen sonuçlar
- **Spike-1 (server+crypto+import, headless), Py3.14:** PASS. Nuitka **zig** (0.16.0) derleyicisini indirip kullandı — MinGW gerekmedi, C-derleyici duvarı böyle aşıldı. clr_loader + webview DLL'leri oto-toplandı. exe çalıştı, exit 0.
- **Spike-2 (pywebview penceresi), Py3.14:** **SEGFAULT (exit 3).** Deneysel-3.14 Nuitka bug'ı (uyarı doğru çıktı). → owner kararı: **Python 3.12'de derle** (son kullanıcı fark etmez, Python exe'de gömülü).
- **Deps + Nuitka → Python 3.12'ye kuruldu** (Nuitka 4.1.3 3.12'de TAM destek). 3.12 ortamında PyQt yok → Qt-çakışması da yok.
- **Spike-2 Py3.12:** segfault GİTTİ. Yeni sorun: Nuitka'nın **pywebview plugin'i** (`PywebViewPlugin.py`) pywebview 6.2.1 için ESKİ — Windows listesine `webview.platforms.win32` eklememiş ama 6.2.1'in `winforms.py`'ı onu koşulsuz import ediyor → ImportError. `--include-package=webview` denemesi plugin ile çakıştı (`webview.platforms.android` FATAL).
- **★ KAZANAN REÇETE (Spike-2 Py3.12 → PASS, pencere açıldı):**
  `py -3.12 -m nuitka --standalone --assume-yes-for-downloads`
  `--nofollow-import-to=PyQt5,PyQt6,PySide2,PySide6,tkinter`
  `--disable-plugin=pywebview` (eski plugin yerine elle yönet)
  `--include-module=webview.platforms.winforms,win32,edgechromium,mshtml` (ayrı ayrı) `--include-module=clr`
- **Kod değişikliği:** `routes.py` frozen-farkında yol (`__compiled__`/`sys.frozen` → `sys.executable` yanı). `kasa_app.py` tepe-seviye giriş (Nuitka'nın `src`'yi çözmesi için). `src.tray`/`src.distill` KASITEN dahil edilmedi (tray PyQt5 çeker; distill Ollama). `--include-package=src.vault,src.mcp_server,src.dashboard,src.desktop` + `--include-module=src.config`.
- Not: pywebview'ın yamalı bir üçüncü-taraf sürümünü kurma seçeneği değerlendirildi, kullanılmadı (3.12'ye geçiş sorunu zaten çözdü).

## ★★ TAM BUILD + DOĞRULAMA: **BAŞARILI** (2026-07-10)
- **`KASA.exe` derlendi** (`build_nuitka_312/kasa_app.dist/KASA.exe`; exe ~55MB, one-folder klasörünün
  tamamı ~104MB). Build exit 0.
- **Uçtan-uca PASS:** `KASA_VAULT_PATH=<depo-koku> KASA_SELFTEST=6 KASA.exe` → `SELFTEST server_ready port=65421`, exit 0. Yani derlenmiş native exe: uvicorn'u bg-thread'de başlattı → health OK → **pywebview WebView2 penceresini `/dashboard`'a açtı** (gerçek vault) → tray → temiz kapanış.
- **★ KAYNAK KORUMA DOĞRULANDI (ampirik):** dist'te `src/*.py` = **0**; `redact.py`/`cell_crypt.py`/`server.py` **yok** (native makine koduna derlendi → bytecode-decompile yolu
kapalı; ikili tersine mühendisliğe karşı mutlak koruma İDDİA EDİLMİYOR — bkz. yukarıdaki Kerckhoffs notu);
okunabilir `.pyc` yok. IP-kritik güvenlik kodu (redact desenleri + kripto + vault) makine kodu. UI (dashboard_ui/app.js,index.html) dosya olarak var ama IP değil (tarayıcıda zaten görünür, Kerckhoffs).
- **Sonuç: Nuitka + Python 3.12 ile çalışan, kaynak-korumalı KASA.exe HAZIR.**

## ★★★ FAZ 3 — ONEFILE CİLA: **BAŞARILI** (2026-07-10)
- **Tek dosya `KASA.exe` = 25.2 MB** (`build_nuitka_onefile/KASA.exe`). Payload 104MB→26MB (%25 sıkıştırma). Build exit 0, 251s.
- **Cila uygulandı:** `--onefile` (tek dosya, yanında 57 dosya taşımaz) + `--windows-console-mode=disable` (arka siyah CMD YOK, GUI-subsystem) + `--windows-icon-from-ico=assets/icon.ico` (7 ikon gömüldü) + metadata (product/version/company) + `--onefile-tempdir-spec={CACHE_DIR}\KASA\{VERSION}` (ilk açılışta `%LOCALAPPDATA%\KASA\0.1.0`'a açar, sonra sıcak/anında).
- **★ ONEFILE RİSKİ ÇÖZÜLDÜ (asıl test):** onefile kendini temp'e açar → `sys.executable` orijinal exe'yi gösterir (temp'i DEĞİL) → eski `sys.executable`-yanı yolu KIRILIRDI. **Düzeltme:** `routes.py::_resolve_ui_dir()` artık `__compiled__.containing_dir` (Nuitka kanonik ikili-dizini = onefile'da temp kök) kullanıyor + aday-listesinden `index.html`'i ilk bulan kök seçiliyor (mühür=ölçüm, yanlış-yolu yutmaz). `__file__` yedeği onefile'ı ayrıca yakalar.
- **Uçtan-uca PASS:** `Start-Process -Wait` (GUI-subsystem exe `&` ile beklenmez!) + stdout redirect → `SELFTEST server_ready port=52634`, **exit 0**, 11.3s (temp açılım + 8s selftest). Server bg-thread + pywebview `/dashboard` gerçek vault + temiz kapanış.
- **★ KAYNAK KORUMA (açılım dizininde bile) DOĞRULANDI:** `%LOCALAPPDATA%\KASA\0.1.0` içinde `src/*.py` = **0**; `redact.py`/`cell_crypt.py`/`server.py`/`routes.py`/`stats.py` **YOK** (native). Saldırgan açılımı incelese bile IP-kritik kaynak orada değil. `dashboard_ui/index.html` açılımda VAR (UI aseti, Kerckhoffs).
- **Reçete sabitlendi:** `build_kasa.ps1` (varsayılan onefile; `-Standalone` ile debug klasör modu). 3.12 kalkanı script'te (3.14 bulursa `throw`).
- **Sonuç: tek-dosya, konsolsuz, ikonlu, kaynak-korumalı KASA.exe (25.2 MB) HAZIR.**
- **Küçük uyarı (bloklamaz):** "Cannot find Windows Runtime DLLs" — hedef makinede VC++ runtime/WebView2 kurulu olmalı (Win10/11'de genelde var). İmza/installer Faz 4'te bunu ele alır.

## ★★★★ BAĞIMLILIK ÖN-KONTROLÜ + KULLANIM ŞARTLARI (2026-07-10)
İstek: "eksik olan parçaları tespit etsin, gerekenleri indir desin + kullanım şartları elbette gösterilsin."
- **Preflight (`src/desktop/preflight.py`):** WebView2 Runtime (registry GUID `{F3017226-...}`, HKLM WOW6432+64+32 view + HKCU) + VC++ 2015-2022 x64 (registry `VC\Runtimes\X64` + `vcruntime140.dll` yedeği) **YEREL** tespit (ag YOK). Eksikse `Dependency(name, reason, url, critical)` listesi; URL'ler **resmi MS** (WebView2 evergreen bootstrapper `go.microsoft.com/fwlink?LinkId=2124703`, vc_redist `aka.ms/vs/17/release/vc_redist.x64.exe`). Test kancasi `KASA_PREFLIGHT_SIMULATE_MISSING=webview2,vcredist`.
- **launch.py `_preflight_gate()`:** pencereden ÖNCE çalışır. Kritik eksik (WebView2) → native Win32 MessageBox (MB_YESNO, ctypes user32) "indirme sayfasını açayım mı?" → evet: `webbrowser.open(resmi MS URL)`, `return 3` (pencere açılmaz). Yalnız-tavsiye eksik (vcredist) → bilgi kutusu + link + devam. Auto-exec YOK (kullanıcı MS'ten indirir). Bagimliliklar mevcutsa sessizce geçer.
- **Kullanım şartları:** `TERMS_OF_USE.md` (kanonik, sürüm 1.0, dürüst güvenlik beyanı — "askeri/kurumsal düzey" iddiası YOK, at-rest kademeli açıkça belirtilir) + `dashboard_ui/terms.html` (self-contained/air-gap, token enjekte, kabul-onay checkbox). Kabul kaydı `src/desktop/consent.py` → `<DATA_DIR>/acceptance.json` (sürüm + ts, atomik yaz). Rotalar (routes.py): `GET /terms` (owner UI), `GET /v1/terms/status` + `POST /v1/terms/accept` (bearer). launch.py start-URL = `/terms` (kabul edilmemişse) → JS kabul sonrası `/dashboard`'a yönlendirir; kabul edilmişse doğrudan pano.
- **Testler:** `test_preflight.py` (5) + `test_terms_gate.py` (6) = **11 yeni**; tüm suite **135 passed, 1 xfailed** (önceki 124, regresyon yok).
- **★ ONEFILE CANLI DOĞRULAMA (derlenmiş binary):** cache temizle → taze config (terms kabul edilmemiş) → server 1s'de hazır (preflight geçti = deps mevcut) → `/terms` 200 (6775B, şartlar metni, token enjekte, placeholder yok) → `/v1/terms/status` bearer → `{"accepted":false}` → `/dashboard` 200 → selftest exit 0. **Kaynak-koruma açılımda korunuyor:** preflight.py/consent.py/redact/cell_crypt/routes hepsi **native (YOK)**, `src/*.py`=0, terms.html bundle'da.
- **★ ÖĞRENME (build kilidi):** onefile rebuild `PermissionError WinError 5` verdi — eski `KASA.exe` çalışan bir örnek tarafından kilitliydi (açık pencere + `%LOCALAPPDATA%\KASA\0.1.0` altındaki açılım süreci). Nuitka eski exe'yi `os.unlink` edemedi. **Düzeltme:** `build_kasa.ps1` artık derlemeden ÖNCE `Get-Process KASA | Stop-Process`. Ayrıca **sabit `{VERSION}` cache bayat kalabilir** — aynı sürümde yeniden derlerken `%LOCALAPPDATA%\KASA\{VERSION}` elle temizle (yoksa eski terms.html/kod servis edilir).

## Sıradaki (Faz 4 — dağıtım, owner kararı)
- Kod imzalama sertifikası (SmartScreen uyarısını kaldırır) + installer (Inno Setup/MSIX) + WebView2/VC++ runtime bootstrap (preflight zaten tespit+yönlendirme yapıyor; installer bunu otomatikleştirebilir).
- Not: **her zaman `py -3.12`** (3.14 pywebview segfault). Build: `pwsh -File build_kasa.ps1`.
