# kasa/src/vault/cell_crypt.py

"""
Hucre-basina (per-cell) at-rest sifreleme — L2 hibrit app-layer AES-GCM.

Bir DB hucresinin (TEXT kolon) icerigini sifreler; ciphertext base64 ile "K1:" onekli
TEXT olarak saklanir. Boylece profile.value / events.content / audit.details kolonlarinin
DUZ METNI SQLite motoruna hic girmez -> kasa.db + -wal/-shm/-journal yalniz ciphertext tutar.

Anahtar: DPAPI-korumali .vaultkey (KeyProvider dikisi; bugun DPAPI/Windows, yarin macOS
Keychain AYNI arayuze takilir). AAD hucreyi baglamina baglar (table|column|context) ->
satir/kolon takas saldirisi decrypt'i InvalidTag ile bozar.

Neden yeni modul (src/export/encrypt.py degil): encrypt.py TUM-KASA dosya-ihracatcisidir
(export_vault/verify_export), hucre-primitifi degil. Bu, ayri, versiyonlu, AAD'li primitif.

Migrasyon-guvenligi: decrypt_cell, "K1:" oneki OLMAYAN hucreyi legacy-plaintext kabul edip
AYNEN dondurur -> kod deploy olduktan sonra ama migration kosmadan once eski satirlar hala
okunur; yeni yazimlar sifrelenir; migration eski satirlari cevirir.
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from . import encryption

PREFIX = "K1:"              # sifreli-hucre imzasi + migrasyon-durumu tespiti (idempotency guard)
KEY_FILE_NAME = ".vaultkey"
_NONCE_LEN = 12


# --- KeyProvider dikisi (bugun DPAPI/Windows; macOS portunda Keychain provider buraya) ---
def load_key(vault_path: str) -> bytes:
    """{vault_path}/.vaultkey'i DPAPI ile cozup 32-byte AES-256 anahtarini dondurur.
    NOT: mevcut deploy'da vault_password kullanilmiyor; kullanilirsa bu anahtar Vault._db_key
    ile ayrisir (o durumda cagiran taraf key'i acikca gecmeli) -> THREAT_MODEL reziduel."""
    with open(os.path.join(vault_path, KEY_FILE_NAME), "rb") as f:
        return encryption.unprotect_data(f.read())


def is_encrypted(cell) -> bool:
    """Hucre 'K1:' onekli sifreli hucre mi? (str olmayan / None guvenli)."""
    return isinstance(cell, str) and cell.startswith(PREFIX)


def encrypt_cell(plaintext: str, key: bytes, aad: str) -> str:
    """plaintext(str) -> 'K1:' + base64(nonce(12) + ciphertext+tag). AAD bagi zorunlu.
    Nonce her cagride os.urandom -> ayni plaintext bile her seferinde farkli ciphertext."""
    if plaintext is None:
        plaintext = ""
    nonce = os.urandom(_NONCE_LEN)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), aad.encode("utf-8"))
    return PREFIX + base64.b64encode(nonce + ct).decode("ascii")


def decrypt_cell(cell: str, key: bytes, aad: str) -> str:
    """'K1:' onekli hucreyi cozer. Onek YOKSA legacy plaintext kabul edilip AYNEN dondurulur
    (migrasyon-oncesi/sirasi seffaf okuma). AAD/anahtar uyusmazsa AESGCM InvalidTag firlatir."""
    if not is_encrypted(cell):
        return cell  # legacy plaintext (pre-migration) — seffaf gecis
    raw = base64.b64decode(cell[len(PREFIX):])
    nonce, ct = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
    return AESGCM(key).decrypt(nonce, ct, aad.encode("utf-8")).decode("utf-8")


# --- AAD kurucular (her kolon icin baglam; decrypt tarafinda AYNI baglamla yeniden uretilir) ---
def aad_profile(key_name: str) -> str:
    return f"profile|value|{key_name}"


def aad_event() -> str:
    # events.content: sabit AAD (kolon-takas'i onler; satir-takas'i events-ici dusuk risk, THREAT_MODEL)
    return "events|content"


def aad_audit(agent_id: str, action: str, timestamp) -> str:
    return f"audit|details|{agent_id}|{action}|{timestamp}"
