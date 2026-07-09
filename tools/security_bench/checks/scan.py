import subprocess
import sys
import json
import importlib.util

def run():
    results = []
    
    # Bandit Scan
    if importlib.util.find_spec("bandit") is None:
        result = {
            "id": "SCAN-BANDIT",
            "category": "scan",
            "title": "Static Analysis with Bandit",
            "status": "SKIP",
            "severity": "info",
            "evidence": "Bandit not installed. Remediation: pip install bandit.",
            "remediation": "pip install bandit; review src findings"
        }
        results.append(result)
    else:
        try:
            # Controller: .bak yedekleri src/ disina tasindi (_bak_archive) -> exclude'a gerek yok, gercek src taranir.
            cmd = [sys.executable, "-m", "bandit", "-r", "src", "-f", "json"]
            process = subprocess.run(cmd, cwd="d:/kasa", capture_output=True, text=True, timeout=300)
            data = process.stdout
            try:
                results_data = json.loads(data)
                high_issues = sum(1 for result in results_data["results"] if result["issue_severity"] == "HIGH")
                medium_issues = sum(1 for result in results_data["results"] if result["issue_severity"] == "MEDIUM")
                
                status = "PASS"
                evidence = f"High: {high_issues}, Medium: {medium_issues}"
                if high_issues > 0:
                    status = "FAIL"
                    evidence += "; Found HIGH severity issues."
                elif medium_issues > 0:
                    status = "WARN"
                    evidence += "; Found MEDIUM severity issues."
                
                result = {
                    "id": "SCAN-BANDIT",
                    "category": "scan",
                    "title": "Static Analysis with Bandit",
                    "status": status,
                    "severity": "high",
                    "evidence": evidence,
                    "remediation": "pip install bandit; review src findings"
                }
                results.append(result)
            except json.JSONDecodeError:
                result = {
                    "id": "SCAN-BANDIT",
                    "category": "scan",
                    "title": "Static Analysis with Bandit",
                    "status": "FAIL",
                    "severity": "high",
                    "evidence": f"Failed to parse output: {data[:200]}",
                    "remediation": "pip install bandit; review src findings"
                }
                results.append(result)
        except subprocess.TimeoutExpired:
            result = {
                "id": "SCAN-BANDIT",
                "category": "scan",
                "title": "Static Analysis with Bandit",
                "status": "FAIL",
                "severity": "high",
                "evidence": "Scan timed out.",
                "remediation": "pip install bandit; review src findings"
            }
            results.append(result)
        except Exception as e:
            result = {
                "id": "SCAN-BANDIT",
                "category": "scan",
                "title": "Static Analysis with Bandit",
                "status": "SKIP",
                "severity": "info",
                "evidence": f"Unexpected error: {str(e)}",
                "remediation": "pip install bandit"
            }
            results.append(result)
    
    # Pip Audit Scan
    if importlib.util.find_spec("pip_audit") is None:
        result = {
            "id": "SCAN-PIPAUDIT",
            "category": "scan",
            "title": "Dependency Audit with pip-audit",
            "status": "SKIP",
            "severity": "info",
            "evidence": "pip-audit not installed. Remediation: pip install pip-audit.",
            "remediation": "pip install pip-audit; review requirements.txt findings"
        }
        results.append(result)
    else:
        try:
            cmd = [sys.executable, "-m", "pip_audit", "-r", "requirements.txt", "-f", "json"]
            process = subprocess.run(cmd, cwd="d:/kasa", capture_output=True, text=True, timeout=300)
            data = process.stdout
            try:
                results_data = json.loads(data)
                if isinstance(results_data, dict):
                    results_data = results_data["dependencies"]
                
                vulnerable_count = sum(1 for entry in results_data if "vulns" in entry and entry["vulns"])
                
                status = "PASS"
                evidence = f"Vulnerable dependencies: {vulnerable_count}"
                if vulnerable_count > 0:
                    status = "FAIL"
                    evidence += "; Found vulnerable dependencies."
                
                result = {
                    "id": "SCAN-PIPAUDIT",
                    "category": "scan",
                    "title": "Dependency Audit with pip-audit",
                    "status": status,
                    "severity": "high",
                    "evidence": evidence,
                    "remediation": "pip install pip-audit; review requirements.txt findings"
                }
                results.append(result)
            except json.JSONDecodeError:
                result = {
                    "id": "SCAN-PIPAUDIT",
                    "category": "scan",
                    "title": "Dependency Audit with pip-audit",
                    "status": "FAIL",
                    "severity": "high",
                    "evidence": f"Failed to parse output: {data[:200]}",
                    "remediation": "pip install pip-audit; review requirements.txt findings"
                }
                results.append(result)
        except subprocess.TimeoutExpired:
            result = {
                "id": "SCAN-PIPAUDIT",
                "category": "scan",
                "title": "Dependency Audit with pip-audit",
                "status": "FAIL",
                "severity": "high",
                "evidence": "Scan timed out.",
                "remediation": "pip install pip-audit; review requirements.txt findings"
            }
            results.append(result)
        except Exception as e:
            result = {
                "id": "SCAN-PIPAUDIT",
                "category": "scan",
                "title": "Dependency Audit with pip-audit",
                "status": "SKIP",
                "severity": "info",
                "evidence": f"Unexpected error: {str(e)}",
                "remediation": "pip install pip-audit"
            }
            results.append(result)
    
    # Secrets Scan
    if importlib.util.find_spec("detect_secrets") is None:
        result = {
            "id": "SCAN-SECRETS",
            "category": "scan",
            "title": "Secret Detection with Detect-Secrets",
            "status": "SKIP",
            "severity": "info",
            "evidence": "Detect-secrets not installed. Remediation: pip install detect-secrets.",
            "remediation": "pip install detect-secrets; review filesystem findings"
        }
        results.append(result)
    else:
        try:
            # Controller splice: path'siz 'scan' repo'yu taramiyordu (sahte PASS=0). --all-files ile
            # gercek dosyalar taranir; .pytest_cache (sabit CACHEDIR.TAG) false-positive olarak haric.
            cmd = [sys.executable, "-m", "detect_secrets", "scan", "--all-files", "--exclude-files", r"\.pytest_cache"]
            process = subprocess.run(cmd, cwd="d:/kasa", capture_output=True, text=True, timeout=300)
            data = process.stdout
            try:
                results_data = json.loads(data)
                total_findings = sum(len(v) for v in results_data["results"].values())
                
                status = "PASS"
                evidence = f"Total findings: {total_findings}"
                if total_findings > 0:
                    status = "FAIL"
                    first_file = next(iter(results_data["results"]))
                    evidence += f"; First file with secrets: {first_file}"
                
                result = {
                    "id": "SCAN-SECRETS",
                    "category": "scan",
                    "title": "Secret Detection with Detect-Secrets",
                    "status": status,
                    "severity": "critical",
                    "evidence": evidence,
                    "remediation": "Review filesystem findings"
                }
                results.append(result)
            except json.JSONDecodeError:
                result = {
                    "id": "SCAN-SECRETS",
                    "category": "scan",
                    "title": "Secret Detection with Detect-Secrets",
                    "status": "FAIL",
                    "severity": "critical",
                    "evidence": f"Failed to parse output: {data[:200]}",
                    "remediation": "Review filesystem findings"
                }
                results.append(result)
        except subprocess.TimeoutExpired:
            result = {
                "id": "SCAN-SECRETS",
                "category": "scan",
                "title": "Secret Detection with Detect-Secrets",
                "status": "FAIL",
                "severity": "critical",
                "evidence": "Scan timed out.",
                "remediation": "Review filesystem findings"
            }
            results.append(result)
        except Exception as e:
            result = {
                "id": "SCAN-SECRETS",
                "category": "scan",
                "title": "Secret Detection with Detect-Secrets",
                "status": "SKIP",
                "severity": "info",
                "evidence": f"Unexpected error: {str(e)}",
                "remediation": "pip install detect-secrets; review filesystem findings"
            }
            results.append(result)
    
    # Controller: KALICI HIJYEN kontrolu — src/ icinde .bak/yedek birikimi -> WARN.
    # Tek-seferlik 'mv' degil; benchmark her kosuda denetler (aksi halde ~6 ayda yine 18 tane birikir).
    try:
        import os
        bak_files = []
        for root, _dirs, files in os.walk("d:/kasa/src"):
            for fn in files:
                if "bak_" in fn or fn.endswith(".bak"):
                    bak_files.append(fn)
        results.append({
            "id": "SCAN-BAK-HYGIENE",
            "category": "scan",
            "title": "No backup (.bak) files under src/",
            "status": "PASS" if not bak_files else "WARN",
            "severity": "medium",
            "evidence": "No .bak/backup files under src/" if not bak_files
                        else f"{len(bak_files)} backup files under src/: " + ", ".join(bak_files[:5]),
            "remediation": "Move .bak/backup files out of src/ (e.g. _bak_archive) so scans stay honest"
        })
    except Exception as e:
        results.append({"id": "SCAN-BAK-HYGIENE", "category": "scan", "title": "Backup hygiene check",
                        "status": "SKIP", "severity": "info", "evidence": str(e), "remediation": ""})

    return results


# ===== NEDEN -> SONUC / CAUSE -> EFFECT (yerel model, sifir-token) =====
# Purpose: This script runs security scans using Bandit, pip-audit, and Detect-Secrets.
# Why (cause -> effect): By scanning the codebase for vulnerabilities, dependencies, and secrets,
# it helps identify potential security issues early in the development process.
# Amac: Bu betik, Bandit, pip-audit ve Detect-Secrets kullanarak güvenlik taramaları çalıştırır.
# Neden -> Sonuc: Kod tabanını zafiyetler, bağımlılıklar ve gizli anahtarlar açısından inceleyerek,
# geliştirme sürecinin başlarında olası güvenlik sorunlarını erkenden belirlemeye yardımcı olur.
