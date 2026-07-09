# KASA Security Benchmark — paket giris noktasi (python -m tools.security_bench).
# Glue yalnizca; tum mantik run.py ve checks/* icinde (yerel pipeline uretir).
from tools.security_bench.run import main

if __name__ == "__main__":
    raise SystemExit(main())
