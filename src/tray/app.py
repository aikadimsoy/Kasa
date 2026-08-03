import os
import sys
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QApplication, QMenu, QAction, QSystemTrayIcon

# d:/kasa'yı sys.path'e ekle
sys.path.append(os.path.abspath(os.path.join('d:', 'kasa')))

# DistillEngine'i buradan içe aktar
from src.distill.engine import DistillEngine

class KasaTrayApp:
    def __init__(self):
        self._locked = True  # Başlangıçta kasayı kilitle
        self.tray_icon = QSystemTrayIcon(self.create_icon(), parent=None)
        self.menu = QMenu()
        self.update_context_menu()
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def create_icon(self):
        icon = QIcon()
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor("#4C8DFF"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        painter.drawRect(0, 0, 15, 15)
        painter.end()
        icon.addPixmap(pixmap)
        return icon

    def update_context_menu(self):
        self.status_label = QAction("Kilitli")
        self.status_label.setEnabled(False)
        self.menu.addAction(self.status_label)
        self.menu.addSeparator()
        self.unlock_action = QAction("Kasayi Ac")
        self.unlock_action.triggered.connect(self.vault_unlock)
        self.menu.addAction(self.unlock_action)
        self.lock_action = QAction("Kasayi Kilitle")
        self.lock_action.triggered.connect(self.vault_lock)
        self.menu.addAction(self.lock_action)
        self.menu.addSeparator()
        self.distill_action = QAction("Distillasyon Calistir")
        self.distill_action.triggered.connect(self.run_distill)
        self.menu.addAction(self.distill_action)
        self.browser_action = QAction("Tarayiciyi Ac")
        self.browser_action.triggered.connect(self.open_browser_window)
        self.menu.addAction(self.browser_action)
        self.menu.addSeparator()
        self.exit_action = QAction("Cikis")
        self.exit_action.triggered.connect(self.quit_app)
        self.menu.addAction(self.exit_action)

    def vault_unlock(self):
        self._locked = False
        self.status_label.setText("Açık")
        self.tray_icon.showMessage("Kasa Açıldı", "Kasayı başarıyla açtınız.", QSystemTrayIcon.Information)

    def vault_lock(self):
        self._locked = True
        self.status_label.setText("Kilitli")
        self.tray_icon.showMessage("Kasa Kilitlendi", "Kasayı başarıyla kilitleyiniz.", QSystemTrayIcon.Information)

    def run_distill(self):
        class DistillThread(QThread):
            finished = pyqtSignal(str)

            def run(self):
                try:
                    # Turkce not: sabit 'd:/kasa/kasa.db' YERINE depo kokunden
                    # turetilir (src/tray/app.py -> parents[2]); repo herhangi
                    # bir dizine klonlanabilsin diye.
                    import pathlib as _pl
                    engine = DistillEngine(
                        db_path=str(_pl.Path(__file__).resolve().parents[2] / "kasa.db"),
                        ollama_url='http://localhost:11434/api/generate'
                    )
                    result = engine.run_batch()
                    processed = result.get('processed', 0)
                    committed = result.get('facts_committed', 0)
                    errors = result.get('errors', [])
                    msg = f"İşlenen: {processed}, Kaydedilen: {committed}"
                    if errors:
                        msg += f" | Hata: {len(errors)}"
                    self.finished.emit(msg)
                except Exception as e:
                    self.finished.emit(f"Hata: {e}")

        # Thread'i instance değişkenine atıyoruz — GC'den korunmak için
        self._distill_thread = DistillThread()
        self._distill_thread.finished.connect(
            lambda msg: self.tray_icon.showMessage("Distillasyon", msg, QSystemTrayIcon.Information)
        )
        self._distill_thread.start()

    def open_browser_window(self):
        # PyQt5 + pywebview aynı process'te çalışamaz — ayrı process aç
        #
        # Turkce not: yorumlayici ve depo kokunun tamami CALISMA-ANINDA turetilir; daha once
        # burada sabit "C:\\Users\\<kullanici>\\...python.exe" ve "d:/kasa" yaziliydi -> repo
        # baska bir makinede/dizinde CALISMIYORDU (ve sahibin hesap adini sizdiriyordu).
        # KASA_PYTHON ile yorumlayici elle gecersiz kilinabilir (donmus/exe dagitim icin).
        import subprocess
        import pathlib
        import sys

        # The browser is opt-in. Tell the user here instead of letting the child
        # process die with a traceback nobody sees.
        #
        # Turkce not: alt surec ayri bir process oldugu icin oradaki RuntimeError
        # kullaniciya HIC gorunmez -- tepsiden tiklar, hicbir sey olmaz, sebebini
        # ogrenemez. Bu yuzden kapiyi burada da soruyoruz: ayni karar, iki yerde
        # sorulur ama tek yerde tanimlidir (browser_enabled).
        from src.browser.browser_window import browser_enabled
        if not browser_enabled():
            self.tray_icon.showMessage(
                "Tarayıcı kapalı",
                "KASA tarayıcısı bu sürümde varsayılan olarak kapalıdır "
                "(bilinen izolasyon açığı — bkz. SECURITY.md). "
                "Açmak için KASA_ENABLE_BROWSER=1 ortam değişkenini ayarlayın.",
                QSystemTrayIcon.Warning,
                8000,
            )
            return

        repo_root = pathlib.Path(__file__).resolve().parents[2]
        python = os.environ.get("KASA_PYTHON") or sys.executable
        env = os.environ.copy()
        try:
            from src.config import load_config
            cfg = load_config(repo_root / "kasa.toml")
            env["KASA_BEARER_TOKEN"] = cfg["server"]["bearer_token"]
        except Exception:
            pass
        subprocess.Popen(
            [python, "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); "
             "from src.browser.browser_window import open_browser; open_browser()",
             str(repo_root)],
            cwd=str(repo_root),
            env=env,
        )

    def quit_app(self):
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Tüm pencereler kapansa da uygulamanın çıkmaması için
    app.setQuitOnLastWindowClosed(False)
    tray_app = KasaTrayApp()
    sys.exit(app.exec_())
