# kasa/kasa_app.py
# KASA masaustu uygulamasi — tepe-seviye giris noktasi (paketleme icin).
# Nuitka/PyInstaller bunu derler; `src` paketi buradan (repo koku) cozulur.
# Calisma mantigi: src/desktop/launch.py.

from src.desktop.launch import main

if __name__ == "__main__":
    raise SystemExit(main())
