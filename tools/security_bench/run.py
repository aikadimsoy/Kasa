import sys
import os
import platform
import socket
import datetime
import json
from tools.security_bench.checks import authz, crypto, audit, scan, fuzz
from tools.security_bench.report import render

def main() -> int:
    try:
        if "d:/kasa" not in sys.path:
            sys.path.insert(0, "d:/kasa")
        
        meta = {
            "date": datetime.datetime.now().isoformat(timespec="seconds"),
            "os": platform.platform(),
            "python": platform.python_version(),
            "host": socket.gethostname()
        }
        
        results = []
        for checker in [authz, crypto, audit, scan, fuzz]:
            try:
                module_results = checker.run()
                if isinstance(module_results, list):
                    results.extend(module_results)
            except Exception as e:
                results.append({
                    "id": f"{checker.__name__}-LOADER",
                    "category": "audit" if checker.__name__.endswith("audit") else "authz" if checker.__name__.endswith("authz") else "crypto" if checker.__name__.endswith("crypto") else "scan",
                    "title": "check module failed to load",
                    "status": "SKIP",
                    "severity": "info",
                    "evidence": str(e),
                    "remediation": "fix module import"
                })
        
        docs = "d:/kasa/docs"
        os.makedirs(docs, exist_ok=True)
        md, js = render(results, meta)
        
        with open(os.path.join(docs, "SECURITY_BENCHMARK.md"), "w", encoding="utf-8") as md_file:
            md_file.write(md)
        
        with open(os.path.join(docs, "security_bench_result.json"), "w", encoding="utf-8") as json_file:
            json_file.write(js)
        
        summary = f"SECURITY BENCHMARK: {'FAIL' if any(r['status'] == 'FAIL' and r['severity'] in ('critical', 'high') for r in results) else 'PASS'} - {len([r for r in results if r['status'] != 'PASS'])} issues found. Report saved at docs/SECURITY_BENCHMARK.md and docs/security_bench_result.json"
        print(summary)
        
        return 1 if any(r['status'] == 'FAIL' and r['severity'] in ('critical', 'high') for r in results) else 0
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())


# ===== NEDEN -> SONUC / CAUSE -> EFFECT (yerel model, sifir-token) =====
# Purpose: The main function of this script is to run a series of security checks and generate reports.
# Why (cause -> effect): By executing various security modules, it identifies vulnerabilities and generates both Markdown and JSON reports for documentation.
# Amac: Bu betiğin ana işlevi, bir dizi güvenlik kontrolünü çalıştırmak ve raporlar oluşturmak.
# Neden -> Sonuc: Farklı güvenlik modüllerini çalıştırarak açıkları belirler ve hem Markdown hem de JSON raporları için belgeleme yapar.
