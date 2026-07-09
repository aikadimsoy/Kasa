# kasa/src/export/encrypt.py
"""
Vault'u şifreli .kasa dosyasına aktarma ve doğrulama modülü.

Dosya formatı (binary, sıralı):
  b"KASA"   — 4 bayt sihirli sayı
  uint16    — 2 bayt sürüm (big-endian, şu an = 1)
  salt      — 32 bayt (KDF tuzu)
  nonce     — 12 bayt (AES-GCM nonce)
  ciphertext — değişken uzunluk (AES-GCM 16 bayt tag içerir)

KDF: scrypt(n=2^14, r=8, p=1) — hafıza-sert, GPU dayanıklı
"""

import sqlite3
import os
import json
import hashlib
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MAGIC = b"KASA"
_VERSION = 1


def _derive_key(password: str, salt: bytes) -> bytes:
    """scrypt ile 256-bit şifreleme anahtarı türetir."""
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)


def _encrypt_data(plaintext: bytes, key: bytes, nonce: bytes) -> bytes:
    """AES-256-GCM ile şifreler; ciphertext+tag döndürür."""
    return AESGCM(key).encrypt(nonce, plaintext, None)


def export_vault(vault_path: str, password: str, output_path: str) -> dict:
    """
    Vault içeriğini şifreli .kasa dosyasına aktarır.

    Args:
        vault_path:  Vault dizini (kasa.db burada aranır).
        password:    Şifreleme parolası.
        output_path: Çıktı dosyası yolu (.kasa uzantısı önerilir).

    Returns:
        {"status": "success", "path": ..., "events": int, "profile": int}
    """
    conn = sqlite3.connect(os.path.join(vault_path, "kasa.db"))
    try:
        conn.row_factory = sqlite3.Row
        events = [dict(row) for row in conn.execute("SELECT * FROM events").fetchall()]
        profile = [dict(row) for row in conn.execute("SELECT * FROM profile").fetchall()]
    finally:
        conn.close()

    plaintext_bytes = json.dumps({"events": events, "profile": profile}).encode("utf-8")

    salt = os.urandom(32)
    nonce = os.urandom(12)
    key = _derive_key(password, salt)
    ciphertext = _encrypt_data(plaintext_bytes, key, nonce)

    with open(output_path, "wb") as f:
        f.write(_MAGIC)
        f.write(struct.pack(">H", _VERSION))
        f.write(salt)
        f.write(nonce)
        f.write(ciphertext)

    return {"status": "success", "path": output_path, "events": len(events), "profile": len(profile)}


def verify_export(output_path: str, password: str) -> dict:
    """
    .kasa dosyasını çözümler ve içeriği doğrular (veri geri yüklemez).

    Args:
        output_path: Doğrulanacak .kasa dosyası.
        password:    Çözümleme parolası.

    Returns:
        {"status": "success", "events": int, "profile": int, "version": int}

    Raises:
        ValueError: Yanlış parola veya bozuk dosya.
    """
    with open(output_path, "rb") as f:
        magic = f.read(4)
        if magic != _MAGIC:
            raise ValueError("Dosya formatı hatalı — KASA sihirli sayısı bulunamadı.")
        version = struct.unpack(">H", f.read(2))[0]
        salt = f.read(32)
        nonce = f.read(12)
        ciphertext = f.read()

    key = _derive_key(password, salt)
    try:
        plaintext_bytes = AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise ValueError("Şifre yanlış veya dosya bozuk.") from e

    data = json.loads(plaintext_bytes.decode("utf-8"))
    return {
        "status": "success",
        "events": len(data["events"]),
        "profile": len(data["profile"]),
        "version": version,
    }
