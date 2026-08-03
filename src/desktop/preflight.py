# kasa/src/desktop/preflight.py

"""
Calisma-zamani bagimlilik on-kontrolu (Windows).

KASA native exe iki Microsoft calisma-zamanina baglidir:
  - **WebView2 Runtime** — pywebview penceresini render eder. Yoksa pencere ACILMAZ (kritik).
  - **VC++ Redistributable (2015-2022 x64)** — CPython 3.12 / uzanti DLL'leri MSVC'ye baglidir.
    Gercekten yoksa exe zaten baslamaz; bu yuzden Python'a kadar gelindiyse tavsiye niteligindedir.

Tasarim ilkeleri:
  - **Tespit tamamen YEREL** (yalniz Windows Registry / DLL varligi okunur; ag YOK).
  - Bir sey eksikse cagiran katman (launch.py) kullaniciya soyler + **resmi Microsoft** indirme
    baglantisini acar. Auto-download/exec YOK (kullanici MS'ten indirir = maksimum guven).
  - Bu, air-gap ilkesiyle celismez: air-gap VAULT VERISININ cihazi terk etmemesiyle ilgilidir;
    isletim-sistemi calisma-zamani kurmak bir kerelik KURULUM isidir, veri akisi degil.

Test kancasi: KASA_PREFLIGHT_SIMULATE_MISSING="webview2,vcredist" ilgili bilesen(ler)i eksik
gosterir (eksik-yol diyalogunu gercekten eksik olmadan denemek icin).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


# WebView2 Evergreen Runtime'in kanonik urun GUID'i (Microsoft belgeleri).
_WEBVIEW2_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"

# Resmi Microsoft indirme baglantilari (evergreen; surum-baski gerektirmez).
_URL_WEBVIEW2 = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"   # MicrosoftEdgeWebview2Setup.exe
_URL_VCREDIST = "https://aka.ms/vs/17/release/vc_redist.x64.exe"


@dataclass(frozen=True)
class Dependency:
    """Eksik bir calisma-zamani bagimliligi + kullaniciya gosterilecek bilgi."""
    key: str            # "webview2" | "vcredist"
    name: str           # insan-okunur ad
    reason: str         # neden gerekli (kullaniciya)
    url: str            # resmi Microsoft indirme baglantisi
    critical: bool      # True ise bu olmadan uygulama calismaz (pencere acilmaz)


def _simulated_missing() -> set[str]:
    raw = os.environ.get("KASA_PREFLIGHT_SIMULATE_MISSING", "")
    return {p.strip().lower() for p in raw.split(",") if p.strip()}


def _reg_value_exists(hive, subkey: str, value: str = "pv") -> bool:
    """Registry'de subkey altinda `value` var ve bos/0.0.0.0 degil mi? (Windows-only)."""
    try:
        import winreg
    except ImportError:
        return False
    for access in (winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
                   winreg.KEY_READ | winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(hive, subkey, 0, access) as k:
                data, _ = winreg.QueryValueEx(k, value)
                if data and str(data) not in ("", "0.0.0.0"):
                    return True
        except (FileNotFoundError, OSError):
            continue
    return False


def webview2_installed() -> bool:
    """WebView2 Runtime kurulu mu? (HKLM makine-genelinde veya HKCU kullanici-basi)."""
    if "webview2" in _simulated_missing():
        return False
    if sys.platform != "win32":
        return True  # Windows disi: pywebview baska backend kullanir; burada engelleme.
    try:
        import winreg
    except ImportError:
        return True
    # Makine-geneli: WOW6432Node yolu (64-bit OS'te client'lar burada), _reg_value_exists ayrica
    # 32/64 view'lari da dener. Per-user: HKCU.
    hklm = winreg.HKEY_LOCAL_MACHINE
    hkcu = winreg.HKEY_CURRENT_USER
    base = r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{}".format(_WEBVIEW2_GUID)
    base_wow = r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{}".format(_WEBVIEW2_GUID)
    return (_reg_value_exists(hklm, base_wow) or _reg_value_exists(hklm, base)
            or _reg_value_exists(hkcu, base))


def vcredist_installed() -> bool:
    """VC++ 2015-2022 x64 redistributable kurulu mu? (registry, DLL varligi yedegi)."""
    if "vcredist" in _simulated_missing():
        return False
    if sys.platform != "win32":
        return True
    try:
        import winreg
    except ImportError:
        return True
    hklm = winreg.HKEY_LOCAL_MACHINE
    if (_reg_value_exists(hklm, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64", "Installed")
            or _reg_value_exists(hklm, r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\X64", "Installed")):
        return True
    # Yedek: yuklu DLL'i dogrudan ara (registry temizlenmis olabilir).
    sysroot = os.environ.get("SystemRoot", r"C:\Windows")
    return os.path.exists(os.path.join(sysroot, "System32", "vcruntime140.dll"))


def missing_dependencies() -> list[Dependency]:
    """Eksik calisma-zamani bagimliliklarini (kritik once) dondurur; hepsi varsa bos liste."""
    out: list[Dependency] = []
    if not webview2_installed():
        out.append(Dependency(
            key="webview2",
            name="Microsoft Edge WebView2 Runtime",
            reason="KASA penceresini goruntulemek icin gereklidir.",
            url=_URL_WEBVIEW2,
            critical=True,
        ))
    if not vcredist_installed():
        out.append(Dependency(
            key="vcredist",
            name="Microsoft Visual C++ 2015-2022 Redistributable (x64)",
            reason="Uygulama calisma-zamani kitaplarini saglar.",
            url=_URL_VCREDIST,
            critical=False,
        ))
    return out
