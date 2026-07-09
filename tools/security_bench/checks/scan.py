import subprocess
import sys
import json
import os
import importlib.util


# ===== L1 secret allowlist suzgeci (test-edilebilir; false-PASS avi icin ayri fonksiyon) =====
def load_allowlist(path=None):
    """secret_allowlist.json -> {(normalize_path, type)} kumesi. Okunamazsa BOS (fail-closed)."""
    path = path or os.path.join(os.path.dirname(__file__), "..", "secret_allowlist.json")
    try:
        with open(path, encoding="utf-8") as f:
            return {(e["path"].replace("\\", "/"), e["type"]) for e in json.load(f)["allowlist"]}
    except Exception:
        return set()


def filter_secrets(results_dict, allow):
    """raw detect-secrets results -> (real_bulgular_listesi, bastirilan_sayi).
    (path,type) allowlist'te ise bastir; degilse 'real'. bearer_token allowlist'te olmadigindan
    HER ZAMAN real'de kalir -> gizlenemez (test bunu kanitlar)."""
    real, suppressed = [], 0
    for path, items in results_dict.items():
        npath = path.replace("\\", "/")
        for it in items:
            if (npath, it["type"]) in allow:
                suppressed += 1
            else:
                real.append(f"{npath}:{it.get('line_number', '?')} [{it['type']}]")
    return real, suppressed


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

                # Controller L1: raw ciktiyi DENETLENMIS allowlist ile suz (secret_allowlist.json).
                # Amac: fixture/false-positive gurultuyu GEREKCELI dusup gercek secret'i (bearer_token)
                # yuzeye cikarmak. bearer_token allowlist'te DEGIL -> FAIL KALIR (durustluk; ".bak gizleme" degil).
                allow_path = os.path.join(os.path.dirname(__file__), "..", "secret_allowlist.json")
                try:
                    with open(allow_path, encoding="utf-8") as _af:
                        allow = {(e["path"].replace("\\", "/"), e["type"]) for e in json.load(_af)["allowlist"]}
                except Exception:
                    allow = set()  # allowlist okunamazsa HICBIR sey bastirma (fail-closed: daha cok FAIL)

                real, suppressed = [], 0
                for path, items in results_data["results"].items():
                    npath = path.replace("\\", "/")
                    for it in items:
                        if (npath, it["type"]) in allow:
                            suppressed += 1
                        else:
                            real.append(f"{npath}:{it.get('line_number', '?')} [{it['type']}]")

                if not real:
                    status = "PASS"
                    evidence = f"0 denetlenmemis secret ({suppressed} allowlist'li bastirildi; gerekce: secret_allowlist.json)"
                else:
                    status = "FAIL"
                    evidence = (f"{len(real)} denetlenmemis secret ({suppressed} allowlist'li bastirildi): "
                                + "; ".join(real[:3]))

                result = {
                    "id": "SCAN-SECRETS",
                    "category": "scan",
                    "title": "Secret Detection with Detect-Secrets (allowlist-suzulmus)",
                    "status": status,
                    "severity": "critical",
                    "evidence": evidence,
                    "remediation": "bearer_token: owner-only ACL uygulandi; kalan -> rotasyon + DPAPI-wrap/at-rest (owner-gated). Yeni bulgu gercekse kaynaktan kaldir, fixture/FP ise gerekceyle secret_allowlist.json'a ekle."
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
    
    # Controller: KALICI HIJYEN — REPO GENELINDE stray .bak/yedek birikimi -> WARN.
    # Onceki surum YALNIZ src/ tariyordu; tools/ + _orch/loop birikimini kacirdi -> 107 dosya (108
    # loop-rollback dahil) sessizce birikmisti. Tek-seferlik 'mv' bir KALICI kontrole baglanmadikca
    # kapanmis sayilmaz. Istisna: _bak_archive (arsivin yeri), kasa.db.bak* (migration yedegi),
    # .git/__pycache__/venv gurultu dizinleri.
    try:
        _repo = "d:/kasa"
        _skip = {"_bak_archive", ".git", "__pycache__", ".pytest_cache",
                 ".venv", "venv", "node_modules"}
        bak_files = []
        for root, dirs, files in os.walk(_repo):
            dirs[:] = [d for d in dirs if d not in _skip]
            for fn in files:
                if fn.startswith("kasa.db.bak"):
                    continue  # migration guvenlik yedegi (bilincli, gitignore'lu)
                if ".bak" in fn or "bak_" in fn:
                    bak_files.append(os.path.relpath(os.path.join(root, fn), _repo).replace("\\", "/"))
        results.append({
            "id": "SCAN-BAK-HYGIENE",
            "category": "scan",
            "title": "No stray backup (.bak) files in repo (excl. _bak_archive)",
            "status": "PASS" if not bak_files else "WARN",
            "severity": "medium",
            "evidence": "No stray backup files in repo" if not bak_files
                        else f"{len(bak_files)} stray backup files (ilk 5): " + ", ".join(sorted(bak_files)[:5]),
            "remediation": "Stray .bak sil/tasi (git rm izliyorsa); loop_runner yedeklerini _bak_archive'a yazmali"
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
