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

    def __init__(self, capacity: int = 60, refill_per_sec: float = 1.0, max_buckets: int = 4096):
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self.max_buckets = max_buckets
        # E1 fix (2026-08-02): kova sozlugu ust siniri. Istemci-beyanli agent_id dondurulunce
        # her yeni kimlik KALICI bir kova aciyordu -> sinirsiz bellek buyumesi (canli olcum:
        # 3000 kimlik -> 3000 kova, tahliye yok). max_buckets asilinca _evict devreye girer.
        self._buckets: dict = {}  # agent_id -> (kalan_token, son_gorulme_monotonic)
        self._lock = threading.Lock()

    def _evict(self, now: float) -> None:
        """Kova sayisi tavani asinca temizler (lock CAGIRAN tarafta tutuluyor olmali).
        Once DURUMSUZ kovalari at: tam dolmus bir kova, hic-gorulmemis ajana ESDEGERDIR
        (silmek ceza degil, yalniz bellek iadesi). Hala tavan ustundeyse en ESKI gorulenleri
        LRU ile at -> sozluk kesin olarak tavanda kalir (hard ceiling)."""
        for aid in [a for a, (t, l) in list(self._buckets.items())
                    if min(float(self.capacity), t + (now - l) * self.refill_per_sec) >= self.capacity]:
            del self._buckets[aid]
        if len(self._buckets) > self.max_buckets:
            oldest = sorted(self._buckets.items(), key=lambda kv: kv[1][1])
            for aid, _ in oldest[:len(self._buckets) - self.max_buckets]:
                del self._buckets[aid]

    def allow(self, agent_id: str, cost: float = 1.0) -> bool:
        """`cost` kadar token düşmeyi dener; yetmezse False (çağrı 429 almalı)."""
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get(agent_id, (float(self.capacity), now))
            tokens = min(float(self.capacity), tokens + (now - last) * self.refill_per_sec)
            if tokens >= cost:
                self._buckets[agent_id] = (tokens - cost, now)
                ok = True
            else:
                self._buckets[agent_id] = (tokens, now)
                ok = False
            # E1: sozluk tavani asti -> temizle. Bu cagriyi yapan kimlik en YENI gorulendir,
            # LRU'da en sonda kalir; yani mevcut cagiran tahliyeden etkilenmez.
            if len(self._buckets) > self.max_buckets:
                self._evict(now)
            return ok

    def reset(self) -> None:
        """Tüm kovaları sıfırlar (test/bakım)."""
        with self._lock:
            self._buckets.clear()
