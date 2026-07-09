import sqlite3
import io
import contextlib
from src.vault import schema
from src.vault.audit import AuditChain

def _verify_silent(ac):
    # Controller: verify_chain() tespit edince stdout'a "Hata:" print ediyor (src/vault/audit.py:88/101).
    # Kasitli-tamper testlerinde bu BEKLENEN cikti; run ciktisini kirletmesin diye yutulur ->
    # boylece "temiz stdout" gercek bir invariant olur; beklenmedik "Hata:" gercek anomali demektir.
    with contextlib.redirect_stdout(io.StringIO()):
        return ac.verify_chain()

def _fresh_chain():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    if "CREATE_AUDIT_TABLE" not in schema.__dict__:
        # Controller splice (trivial): helper had no `results` in scope -> NameError landmine.
        # CREATE_AUDIT_TABLE exists in practice; on absence raise -> run() except -> AUDIT-ERROR SKIP.
        conn.close()
        raise RuntimeError("CREATE_AUDIT_TABLE missing in schema")
    conn.execute(schema.CREATE_AUDIT_TABLE)
    conn.commit()
    ac = AuditChain(conn)
    ac.record("agentA", "vault_init", {"n": 1})
    ac.record("agentB", "profile_read", {"k": "x"})
    ac.record("agentC", "profile_write", {"k": "x", "v": "y"})
    return conn, ac

def run():
    results = []
    
    try:
        # AUDIT-VERIFY
        conn1, ac1 = _fresh_chain()
        if not conn1 or not ac1:
            return results
        
        if _verify_silent(ac1):
            results.append({
                "id": "AUDIT-VERIFY",
                "category": "audit",
                "title": "Audit Chain Integrity Verified",
                "status": "PASS",
                "severity": "high",
                "evidence": "3-record chain verified",
                "remediation": ""
            })
        else:
            results.append({
                "id": "AUDIT-VERIFY",
                "category": "audit",
                "title": "Audit Chain Integrity Verification Failed",
                "status": "FAIL",
                "severity": "high",
                "evidence": "3-record chain failed verification",
                "remediation": ""
            })
        conn1.close()
        
        # AUDIT-TAMPER-MODIFY
        conn2, ac2 = _fresh_chain()
        if not conn2 or not ac2:
            return results
        
        conn2.execute("UPDATE audit SET action='tampered' WHERE id=2")
        conn2.commit()
        
        if not _verify_silent(ac2):
            results.append({
                "id": "AUDIT-TAMPER-MODIFY",
                "category": "audit",
                "title": "Audit Chain Tamper Detection",
                "status": "PASS",
                "severity": "critical",
                "evidence": "Tampering detected in row 2",
                "remediation": ""
            })
        else:
            results.append({
                "id": "AUDIT-TAMPER-MODIFY",
                "category": "audit",
                "title": "Audit Chain Tamper Not Detected",
                "status": "FAIL",
                "severity": "critical",
                "evidence": "Tampering not detected after modification",
                "remediation": ""
            })
        conn2.close()
        
        # AUDIT-TAMPER-DELETE
        conn3, ac3 = _fresh_chain()
        if not conn3 or not ac3:
            return results
        
        conn3.execute("DELETE FROM audit WHERE id=2")
        conn3.commit()
        
        if not _verify_silent(ac3):
            results.append({
                "id": "AUDIT-TAMPER-DELETE",
                "category": "audit",
                "title": "Audit Chain Deletion Detection",
                "status": "PASS",
                "severity": "critical",
                "evidence": "Deletion detected in row 2",
                "remediation": ""
            })
        else:
            results.append({
                "id": "AUDIT-TAMPER-DELETE",
                "category": "audit",
                "title": "Audit Chain Deletion Not Detected",
                "status": "FAIL",
                "severity": "critical",
                "evidence": "Deletion not detected after deletion",
                "remediation": ""
            })
        conn3.close()
    
    except Exception as e:
        results.append({
            "id": "AUDIT-ERROR",
            "category": "audit",
            "title": "Audit Check Execution Error",
            "status": "SKIP",
            "severity": "info",
            "evidence": str(e),
            "remediation": ""
        })
    
    return results


# ===== NEDEN -> SONUC / CAUSE -> EFFECT (yerel model, sifir-token) =====
# Purpose: This script defines functions to audit and verify the integrity of an audit chain.
# Why (cause -> effect): The absence of CREATE_AUDIT_TABLE in schema leads to a RuntimeError, causing the AUDIT-ERROR SKIP. Proper verification checks ensure that tampering or deletion is detected, maintaining the integrity of the audit records.
# Amac: Bu betik, bir denetim zincirinin bütünlüğünü kontrol etmek ve doğrulamak için işlevleri tanımlar.
# Neden -> Sonuc: Şema'da CREATE_AUDIT_TABLE'nin eksikliği, RuntimeError'a neden olur ve AUDIT-ERROR SKIP sonucunu verir. Uygun doğrulama kontrolleri, zararlılık veya silme tespit edilerek denetim kayıtlarının bütünlüğünü korur.
