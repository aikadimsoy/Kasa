# -*- coding: utf-8 -*-
"""Gercek KASA browser'ini coveryourtracks.eff.org'a yonlendirip test sonuc
sayfasinin metnini yakalar. Sadece capture/orkestrasyon -- analiz yerel modele birakilir."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "eff_capture.txt")

env = dict(os.environ)
env["KASA_HEALTHCHECK_URL"] = "https://coveryourtracks.eff.org/"
env["KASA_HEALTHCHECK_MS"] = "30000"  # test otomatik calisip /results'a yonlenmesi icin
env["KASA_CAPTURE_OUT"] = OUT
env["PYTHONPATH"] = REPO
# Deliberate opt-in for a red-team run (see browser_window.browser_enabled).
# Turkce not: tarayici varsayilan KAPALI; olcum kosusu kapiyi yalniz bu alt surec
# icin bilerek acar, kullanicinin ortamini degistirmeden.
env["KASA_ENABLE_BROWSER"] = "1"

py = os.environ.get("KASA_PY") or sys.executable  # sabit yol yerine calisma-ani yorumlayici
code = "import sys; sys.path.insert(0, r'%s\\src\\browser'); import browser_window; browser_window.open_browser()" % REPO
subprocess.run([py, "-c", code], env=env, cwd=REPO, timeout=60)

print("CAPTURED:", OUT, os.path.exists(OUT), os.path.getsize(OUT) if os.path.exists(OUT) else 0)
