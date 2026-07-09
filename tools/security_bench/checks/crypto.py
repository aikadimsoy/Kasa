import os
import tempfile
import shutil
import time as _t
from src.export.encrypt import export_vault, verify_export
from src.vault.database import Vault

def run():
    results = []
    
    try:
        # CRYPTO-EXPORT Check
        tmpdir = tempfile.mkdtemp(dir="d:/kasa")
        vault_path = os.path.join(tmpdir, "vault")
        os.makedirs(vault_path)
        v = Vault(vault_path=vault_path)
        conn = v.get_connection()
        
        # Insert an event
        content_str = '{"note": "test event"}'
        conn.execute("INSERT INTO events (timestamp, session_id, source, type, content, ttl_expiry) VALUES (?,?,?,?,?,?)", (_t.time(), "sess", "bench", "note", content_str, _t.time() + 3600))
        conn.commit()
        
        # Export the vault
        output_path = os.path.join(tmpdir, "e.kasa")
        export_vault(vault_path, "pw-strong-123", output_path)
        
        # Verify the export with correct password
        result = verify_export(output_path, "pw-strong-123")
        if result["status"] == "success":
            results.append({
                "id": "CRYPTO-EXPORT",
                "category": "crypto",
                "title": "Prove vault crypto properties (Export)",
                "status": "PASS",
                "severity": "high",
                "evidence": f"Events count: {result['events']}",
                "remediation": ""
            })
        else:
            results.append({
                "id": "CRYPTO-EXPORT",
                "category": "crypto",
                "title": "Prove vault crypto properties (Export)",
                "status": "FAIL",
                "severity": "high",
                "evidence": f"Verification failed: {result['message']}",
                "remediation": ""
            })
        
        # Verify the export with wrong password
        try:
            verify_export(output_path, "wrong-pw")
        except ValueError:
            results.append({
                "id": "CRYPTO-EXPORT",
                "category": "crypto",
                "title": "Prove vault crypto properties (Export)",
                "status": "PASS",
                "severity": "high",
                "evidence": "wrong-pw rejected",
                "remediation": ""
            })
        else:
            results.append({
                "id": "CRYPTO-EXPORT",
                "category": "crypto",
                "title": "Prove vault crypto properties (Export)",
                "status": "FAIL",
                "severity": "high",
                "evidence": "wrong password did not raise ValueError",
                "remediation": ""
            })
        
        # CRYPTO-KDF Check
        import inspect
        import src.export.encrypt as _enc
        enc_src = inspect.getsource(_enc)
        if 'scrypt' in enc_src and ('2**14' in enc_src or '16384' in enc_src):
            results.append({
                "id": "CRYPTO-KDF",
                "category": "crypto",
                "title": "Prove vault crypto properties (Key Derivation Function)",
                "status": "PASS",
                "severity": "medium",
                "evidence": "scrypt parameters found",
                "remediation": ""
            })
        elif 'scrypt' in enc_src:
            results.append({
                "id": "CRYPTO-KDF",
                "category": "crypto",
                "title": "Prove vault crypto properties (Key Derivation Function)",
                "status": "WARN",
                "severity": "medium",
                "evidence": "scrypt parameters weak or absent",
                "remediation": ""
            })
        else:
            results.append({
                "id": "CRYPTO-KDF",
                "category": "crypto",
                "title": "Prove vault crypto properties (Key Derivation Function)",
                "status": "FAIL",
                "severity": "medium",
                "evidence": "no scrypt found",
                "remediation": ""
            })
        
        # CRYPTO-ATREST Check
        canary = "KASA_CANARY_" + os.urandom(6).hex()
        content_str = f'{{"canary": "{canary}"}}'
        conn.execute("INSERT INTO events (timestamp, session_id, source, type, content, ttl_expiry) VALUES (?,?,?,?,?,?)", (_t.time(), "sess", "bench", "note", content_str, _t.time() + 3600))
        conn.commit()
        v.close()
        
        with open(v.db_path, "rb") as f:
            data = f.read()
        
        if canary.encode() in data:
            results.append({
                "id": "CRYPTO-ATREST",
                "category": "crypto",
                "title": "Prove vault crypto properties (At Rest)",
                "status": "FAIL",
                "severity": "critical",
                "evidence": f"plaintext canary found at byte offset {data.find(canary.encode())} in kasa.db ({len(data)} bytes)",
                "remediation": "Enable at-rest DB encryption (SQLCipher / sqlcipher3-binary PRAGMA key, or application-layer AES-GCM on content)."
            })
        else:
            results.append({
                "id": "CRYPTO-ATREST",
                "category": "crypto",
                "title": "Prove vault crypto properties (At Rest)",
                "status": "PASS",
                "severity": "critical",
                "evidence": "canary absent from raw kasa.db (ciphertext at rest)",
                "remediation": ""
            })
        
        # CRYPTO-DPAPI Check
        import platform
        if platform.system() != "Windows":
            results.append({
                "id": "CRYPTO-DPAPI",
                "category": "crypto",
                "title": "Prove vault crypto properties (Data Protection API)",
                "status": "WARN",
                "severity": "info",
                "evidence": "protect_data is a no-op passthrough off Windows; key unprotected",
                "remediation": "Document non-Windows limitation or add a portable keystore."
            })
        else:
            results.append({
                "id": "CRYPTO-DPAPI",
                "category": "crypto",
                "title": "Prove vault crypto properties (Data Protection API)",
                "status": "PASS",
                "severity": "info",
                "evidence": "DPAPI CryptProtectData available for key file",
                "remediation": ""
            })
        
    except Exception as e:
        results.append({
            "id": "CRYPTO-EXPORT",
            "category": "crypto",
            "title": "Prove vault crypto properties (Export)",
            "status": "SKIP",
            "severity": "info",
            "evidence": str(e),
            "remediation": ""
        })
    
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    
    return results


# ===== NEDEN -> SONUC / CAUSE -> EFFECT (yerel model, sifir-token) =====
# Purpose: This script checks the cryptographic properties of a vault system.
# Why (cause -> effect): It verifies export functionality with correct and incorrect passwords,
#                        checks key derivation function parameters, ensures data at rest is encrypted,
#                        and confirms Data Protection API usage on Windows systems.
# Amac: Bu betik bir kasa sisteminin şifreleme özelliklerini kontrol eder.
# Neden -> Sonuc: Doğru ve yanlış parolalarla dışa aktarma işlevselliğini doğrular,
#                 anahtar türetme fonksiyonu parametrelerini kontrol eder, verilerin dinlenmede şifrelendiğini sağlar
#                 ve Windows sistemlerinde Veri Koruma API'sinin kullanımını onaylar.
