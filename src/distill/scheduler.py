# src/distill/scheduler.py
"""
Gece damıtma (nightly distillation) zamanlayıcısı.
Arka planda daemon thread olarak çalışır; her gece 02:00'de run_nightly() tetikler.
İstenirse manuel olarak da tetiklenebilir.
"""

import os
import threading
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DistillScheduler:
    def __init__(self, db_path: str, ollama_url: str, run_hour: int = 2):
        """
        Args:
            db_path:    Vault SQLite dosya yolu.
            ollama_url: Ollama API adresi.
            run_hour:   Günlük çalışma saati (0-23, varsayılan 02:00).
        """
        self.db_path = db_path
        self.ollama_url = ollama_url
        self.run_hour = run_hour
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_result: dict = {}
        self._last_run_date = None

    def _seconds_until_next_run(self) -> float:
        """Bir sonraki çalışmaya kadar kalan süreyi saniye olarak hesaplar."""
        now = datetime.now()
        next_run = now.replace(hour=self.run_hour, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return (next_run - now).total_seconds()

    def _run_loop(self):
        """Daemon thread ana döngüsü: belirlenen saatte run_nightly() çağırır."""
        logger.info(f"[Scheduler] Baslatildi. Hedef saat: {self.run_hour:02d}:00")
        while not self._stop_event.is_set():
            wait_secs = self._seconds_until_next_run()
            logger.info(f"[Scheduler] Sonraki calistirma: {wait_secs/3600:.1f} saat sonra.")
            # Bekleme süresini küçük dilimler halinde kontrol ederek durdurulabilir yap
            elapsed = 0.0
            while elapsed < wait_secs and not self._stop_event.is_set():
                time.sleep(min(60.0, wait_secs - elapsed))
                elapsed += 60.0

            if self._stop_event.is_set():
                break

            self._trigger()

    def _trigger(self):
        """Damıtma + prune döngüsünü tek seferlik çalıştırır."""
        from .engine import DistillEngine
        logger.info("[Scheduler] Gece damıtma başlıyor...")
        try:
            engine = DistillEngine(self.db_path, self.ollama_url)
            self._last_result = engine.run_batch(max_events=500)
            logger.info(f"[Scheduler] Damıtma tamamlandı: {self._last_result}")
        except Exception as e:
            logger.error(f"[Scheduler] Damıtma hatası: {e}")
            self._last_result = {"error": str(e)}

        # Damıtma sonrası süresi dolmuş event'leri prune et
        try:
            from ..vault.database import Vault
            from ..mcp_server.tools import VaultTools
            vault_path = os.path.dirname(os.path.abspath(self.db_path))
            with Vault(vault_path=vault_path) as vault:
                pruner = VaultTools(vault, agent_id="system")
                prune_result = pruner.prune_expired_events()
                logger.info(f"[Scheduler] Prune tamamlandı: {prune_result}")
        except Exception as e:
            logger.error(f"[Scheduler] Prune hatası: {e}")

        self._last_run_date = datetime.now().date()

    def run_now(self):
        """Zamanlayıcıyı beklemeden hemen tetikler (senkron)."""
        self._trigger()
        return self._last_result

    def start(self):
        """Arka plan zamanlayıcı thread'ini başlatır. Kaçırılan gece çalışması varsa hemen tetikler."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        # Catch-up: bugünün zamanlanmış saati geçmiş ama hiç çalışmadıysa hemen tetikle
        now = datetime.now()
        scheduled_today = now.replace(hour=self.run_hour, minute=0, second=0, microsecond=0)
        if now > scheduled_today and self._last_run_date != now.date():
            logger.info("[Scheduler] Kaçırılan gece çalışması yakalandı, hemen tetikleniyor.")
            threading.Thread(target=self._trigger, daemon=True, name="DistillCatchup").start()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="DistillScheduler")
        self._thread.start()

    def stop(self):
        """Zamanlayıcı thread'ini durdurur."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def last_result(self) -> dict:
        return self._last_result
