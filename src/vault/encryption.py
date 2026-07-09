# kasa/src/vault/encryption.py

"""
Windows Data Protection API (DPAPI) kullanarak veri şifreleme ve şifre çözme.
Bu, kasanın anahtarının kullanıcının Windows oturumuna bağlanmasını sağlar.
Parola gerekmez; anahtar işletim sistemi tarafından yönetilir.
"""

import ctypes
import ctypes.wintypes
import platform

# DPAPI'ye erişim için Windows DLL'lerini ve fonksiyonlarını tanımla
if platform.system() == "Windows":
    # Ctypes yapılarının tanımlanması
    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char))
        ]

    # Fonksiyon prototiplerinin tanımlanması
    crypt_protect_data = ctypes.windll.crypt32.CryptProtectData
    crypt_protect_data.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.wintypes.LPCWSTR,
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB)
    ]
    crypt_protect_data.restype = ctypes.wintypes.BOOL

    crypt_unprotect_data = ctypes.windll.crypt32.CryptUnprotectData
    crypt_unprotect_data.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.POINTER(ctypes.wintypes.LPWSTR),
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB)
    ]
    crypt_unprotect_data.restype = ctypes.wintypes.BOOL

    local_free = ctypes.windll.kernel32.LocalFree
    local_free.argtypes = [ctypes.wintypes.HLOCAL]
    local_free.restype = ctypes.wintypes.HLOCAL

def protect_data(data: bytes, description: str = "Kasa Anahtarı") -> bytes:
    """Verilen byte dizisini DPAPI kullanarak şifreler."""
    if platform.system() != "Windows":
        # Diğer platformlarda geçici olarak şifreleme yapma
        return data

    blob_in = DATA_BLOB(len(data), ctypes.cast(data, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    
    if crypt_protect_data(
        ctypes.byref(blob_in),
        description,
        None,
        None,
        None,
        0, # CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(blob_out)
    ):
        encrypted_data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        local_free(blob_out.pbData)
        return encrypted_data
    else:
        raise RuntimeError("DPAPI ile veri şifreleme başarısız oldu.")

def unprotect_data(encrypted_data: bytes) -> bytes:
    """DPAPI ile şifrelenmiş veriyi çözer."""
    if platform.system() != "Windows":
        # Diğer platformlarda geçici olarak şifreleme yapma
        return encrypted_data

    blob_in = DATA_BLOB(len(encrypted_data), ctypes.cast(encrypted_data, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    
    if crypt_unprotect_data(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0, # CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(blob_out)
    ):
        decrypted_data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        local_free(blob_out.pbData)
        return decrypted_data
    else:
        raise RuntimeError("DPAPI ile veri çözme başarısız oldu.")

if __name__ == '__main__':
    # Hızlı bir test
    original_key = b'Bu_cok_gizli_bir_anahtar_32_byte!'
    print(f"Orijinal Veri: {original_key}")

    encrypted = protect_data(original_key)
    print(f"Şifreli Veri (DPAPI): {encrypted.hex()}")

    decrypted = unprotect_data(encrypted)
    print(f"Çözülmüş Veri: {decrypted}")

    assert original_key == decrypted
    print("\nDPAPI şifreleme ve çözme testi başarılı.")
