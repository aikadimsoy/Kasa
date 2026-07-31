# kasa/src/mcp_server/ratelimit.py

"""
Ajan başına token-bucket hız sınırlayıcı (DEBI-0).

Sebep: halüsinasyon döngüsüne giren bir ajan sınırsız event_ingest/profile_write
çağrısıyla diski ve audit zincirini doldurabilir (yerel DoS). "Model güvenlik
sınırı değildir" (KURALLAR §4) -> fren modele değil deterministik koda konur.
Sonuç: kapasite üstü çağrı ağ katmanında 429 ile reddedilir; kasaya yazma/okuma
debisi üst-sınırlıdır, tek delirmiş ajan diğerlerini etkilemez (kova ajan-başına).
"""

import threading
import time


class RateLimiter:
    """Token-bucket: `capacity` patlama üst sınırı, `refill_per_sec` sürekli debi."""

    def __init__(self, capacity: int = 60, refill_per_sec: float = 1.0):
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self._buckets: dict = {}  # agent_id -> (kalan_token, son_gorulme_monotonic)
        self._lock = threading.Lock()

    def allow(self, agent_id: str, cost: float = 1.0) -> bool:
        """`cost` kadar token düşmeyi dener; yetmezse False (çağrı 429 almalı)."""
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get(agent_id, (float(self.capacity), now))
            tokens = min(float(self.capacity), tokens + (now - last) * self.refill_per_sec)
            if tokens >= cost:
                self._buckets[agent_id] = (tokens - cost, now)
                return True
            self._buckets[agent_id] = (tokens, now)
            return False

    def reset(self) -> None:
        """Tüm kovaları sıfırlar (test/bakım)."""
        with self._lock:
            self._buckets.clear()
