# -*- coding: utf-8 -*-
"""
E1 fix guard: RateLimiter kova sozlugu SINIRSIZ buyumemeli (bellek DoS).

SEBEP (canli olcum 2026-08-02): istemci-beyanli agent_id dondurulunce her yeni kimlik
kalici bir kova aciyordu ve tahliye YOKTU -> 3000 kimlik = 3000 kova, dogrusal bellek
buyumesi. Bu test tavanin (max_buckets) gercekten uygulandigini ve tahliyenin throttle'i
BOZMADIGINI dogrular.
"""
import sys

sys.path.insert(0, "d:/kasa")

from src.mcp_server.ratelimit import RateLimiter  # noqa: E402


def test_bucket_dict_is_bounded():
    """Binlerce donen kimlik -> kova sayisi tavani asamaz (E1 kapali)."""
    rl = RateLimiter(capacity=60, refill_per_sec=1.0, max_buckets=100)
    for i in range(2000):
        rl.allow(f"rotator-{i}")
    assert len(rl._buckets) <= 100, (
        "kova sozlugu tavani asti (E1 hala acik): %d" % len(rl._buckets))


def test_throttle_still_fires_after_eviction_change():
    """NEGATIF KONTROL: tahliye eklemek throttle'i bozmamali -> kapasite bitince 429."""
    rl = RateLimiter(capacity=3, refill_per_sec=0.0, max_buckets=100)  # refill yok: deterministik
    aid = "steady"
    assert rl.allow(aid) is True   # 3 -> 2
    assert rl.allow(aid) is True   # 2 -> 1
    assert rl.allow(aid) is True   # 1 -> 0
    assert rl.allow(aid) is False  # 0 -> reddedilir (throttle calisiyor)


def test_current_caller_survives_eviction():
    """Tahliye aninda cagriyi yapan kimlik (en yeni gorulen) atilmamali."""
    rl = RateLimiter(capacity=5, refill_per_sec=0.0, max_buckets=10)
    for i in range(50):
        rl.allow(f"filler-{i}")
    rl.allow("me")            # 5 -> 4 (kova olusur, tahliye tetiklenir ama 'me' en yeni)
    assert rl.allow("me") is True  # 4 -> 3
    tokens, _ = rl._buckets["me"]
    # Kova korunduysa 3.0; tahliye edilip yeniden yaratilsaydi 4.0 olurdu -> 3.0 = korundu.
    assert tokens == 3.0, "cagiran kovanin durumu korunmadi (tahliye yanlis kimligi atti)"
