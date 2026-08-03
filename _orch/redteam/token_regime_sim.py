# -*- coding: utf-8 -*-
"""
TOKEN REJIMI SIMULASYONU — bir KARAR MODELI (gercek sistem degil, tasarim yardimcisi).

SORU (beyin firtinasi): 'gorev/saat basina donen token + takas' fikri, P1'i (kimligi token'a
    baglama) TAMAMLAR mi, yoksa YERINE mi gecer? Sezgiyle degil, ayni saldirgani uc rejime
    karsi kosturarak cevaplayalim.

MODELLENEN 3 REJIM:
  R1 STATIC_SHARED      — bugunku: TEK ortak token; kimlik istemci-BEYANLI (agent_id govdeden).
  R2 PER_AGENT_STATIC   — P1: her ajanin KENDI (kalici) token'i; kimlik token->ajan haritasindan.
  R3 PER_AGENT_EPHEMERAL— P1 + DONDURME: kimlik yine token'dan, ama token TTL ile suresi dolar.

SALDIRGAN OYUN KITABI (hepsi gecerli bir token'i olan yerel ajan varsayar):
  S1 impersonate('browser')      — ayricalikli kimligi taklit et (F-IMP).
  S2 rotate_identity              — her istekte kimlik degistir (A6 hiz-siniri baypasi).
  S3 steal_and_replay(gecikme)    — mesru bir token'i CAL, gecikme sonra TEKRAR kullan (sizinti).

NOT: Bu bir MANTIK modeli — gercek kripto/vault yok. Amac uc rejimin saldiri karsisindaki
    DAVRANISINI yan yana gormek; boylece 'donen token tamamlayici mi' sorusu olcuye gelir.
"""

R1, R2, R3 = "STATIC_SHARED", "PER_AGENT_STATIC(P1)", "PER_AGENT_EPHEMERAL(P1+rotate)"
TTL = 60.0  # R3'te token omru (sn) — 'saat basi' yerine kisa tutuldu ki sinir gorunsun


class Authority:
    """Token uretir ve bir token+iddiadan GERCEK kimligi cozer (rejime gore)."""

    def __init__(self, regime):
        self.regime = regime
        self._map = {}   # token_value -> (agent, issued_at)
        self._n = 0
        # R1: tek ortak token, kimse ile eslenmez (kimlik iddiadan gelir).
        self.shared = "SHARED-TOKEN" if regime == R1 else None

    def issue(self, agent, now):
        """Bir ajana token verir. R1'de herkes ayni ortak token'i kullanir."""
        if self.regime == R1:
            return self.shared
        self._n += 1
        tok = f"tok-{agent}-{self._n}"
        self._map[tok] = (agent, now)
        return tok

    def resolve(self, token, claimed_agent, now):
        """Sunucunun GORDUGU kimlik. Cozulemezse None (istek reddedilir)."""
        if self.regime == R1:
            # Ortak token dogruysa, sunucu iddiaya INANIR -> istemci-beyanli kimlik.
            return claimed_agent if token == self.shared else None
        rec = self._map.get(token)
        if rec is None:
            return None
        agent, issued = rec
        if self.regime == R3 and (now - issued) >= TTL:
            return None  # sure doldu -> token olu
        # R2/R3: kimlik TOKEN'dan gelir; govdedeki 'claimed_agent' YOK SAYILIR.
        return agent


def sim_impersonate(auth, now):
    """S1: saldirganin kendi token'i var; 'browser' gibi davranmaya calisir."""
    atk_tok = auth.issue("attacker", now)
    seen = auth.resolve(atk_tok, claimed_agent="browser", now=now)
    return "BROWSER OLDU (taklit basarili)" if seen == "browser" else f"engellendi (kimlik='{seen}')"


def sim_rotate(auth, now, k=5):
    """S2: k istek, her birinde farkli iddia. Sunucunun gordugu kimlik kumesi kac farkli?
    Farkliysa kova-basi fren baypas edilir (A6). Tek kimlige coker ise fren tutar."""
    atk_tok = auth.issue("attacker", now)
    seen = {auth.resolve(atk_tok, claimed_agent=f"rot-{i}", now=now) for i in range(k)}
    seen.discard(None)
    if len(seen) > 1:
        return f"BAYPAS ({len(seen)} farkli kimlik -> kova dolmaz)"
    return f"fren tutar (hepsi tek kimlik: {seen or '{reddedildi}'})"


def sim_replay(auth, now, delay):
    """S3: mesru 'browser' token'i t=now'da calinir, now+delay'de tekrar kullanilir."""
    victim_tok = auth.issue("browser", now)
    seen = auth.resolve(victim_tok, claimed_agent="browser", now=now + delay)
    return ("TEKRAR CALISTI (calinan token gecerli)" if seen == "browser"
            else "engellendi (token sureli doldu)")


def run():
    print("\n=== TOKEN REJIMI SIMULASYONU (karar modeli) ===")
    print(f"    R3 TTL = {TTL:.0f} sn\n")
    rows = []
    for regime in (R1, R2, R3):
        a = Authority(regime)
        r_imp = sim_impersonate(a, now=1000.0)
        r_rot = sim_rotate(Authority(regime), now=1000.0)
        r_rep_fast = sim_replay(Authority(regime), now=1000.0, delay=10)     # TTL icinde
        r_rep_slow = sim_replay(Authority(regime), now=1000.0, delay=120)    # TTL sonrasi
        rows.append((regime, r_imp, r_rot, r_rep_fast, r_rep_slow))

    for regime, imp, rot, rf, rs in rows:
        print(f"[{regime}]")
        print(f"   S1 taklit (F-IMP)        : {imp}")
        print(f"   S2 kimlik dondur (A6)    : {rot}")
        print(f"   S3 calip-tekrar (10sn)   : {rf}")
        print(f"   S3 calip-tekrar (120sn)  : {rs}")
        print()

    print("=== DURUST OKUMA ===")
    print("  * Dondurme TEK BASINA yetmez: R1'de kimlik iddiadan geldigi icin kisa omurlu")
    print("    olsa da taklit/baypas surer. Belirleyici olan BAGLAMA (R2), dondurme degil.")
    print("  * R2 (P1) taklit+baypasi kapatir AMA calinan token SURESIZ gecerli (S3 hep calisir).")
    print("  * R3 (P1+dondurme) EK olarak: calinan token TTL sonrasi olur (S3 120sn -> engellendi)")
    print("    ve suresi dolan kova dogal tahliye olur (E1 bedavaya kapanir).")
    print("  * BEDEL: dondurme bir 'yenileme koku' ister (yerelde DPAPI capasi). Kok sizarsa")
    print("    her sey biter (kaplumbaga sorunu). Ayrica CANLI ele gecirmede saldirgan zaten")
    print("    normal yenileme yapar -> dondurme SIZINTIYI daraltir, CANLI ele gecirmeyi durdurmaz.")
    print()


if __name__ == "__main__":
    run()
