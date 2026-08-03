# -*- coding: utf-8 -*-
"""
MEYDAN-OKUMA/CEVAP SIMULASYONU — bir KARAR MODELI (gercek HMAC, ag/vault yok).

FIKIR (beyin firtinasi): giris bileti = FORMUL(token). Yani token'i ele gecirmek yetmesin;
    cikista token'la birlikte bir 'formul' verilsin, geri donuste bu formulun URETTIGI cevap
    giris bileti olsun. Bu, bilinen 'challenge-response / sahiplik kanidi' desenidir.

OLCTUGUMUZ: dort yapilandirmayi (formul acik/gizli x nonce var/yok x anahtar ortak/kisi-basi)
    IKI saldirgana karsi kosturup FARKI gormek:
      - DIS saldirgan (token'i telden gorur, cevabi dinler; ama GIZLI anahtari YOK)
      - IC saldirgan (ortak-anahtarli dunyada anahtari VAR; 'browser'i taklit etmeye calisir)

SONUC (ozet): bilet-formulu ancak (gizli anahtar) + (her istekte nonce) + (kisi-basi anahtar)
    birlikteyken dinleme+replay+taklidi kapatir. Ama CANLI ele gecirmeyi durdurmaz.
"""
import hashlib
import hmac


def mac(key, message):
    """Formul: key=None ise ACIK (anahtarsiz sha256), aksi halde GIZLI HMAC-SHA256.
    Algoritma her zaman aciktir (Kerckhoffs); gizli olan yalniz ANAHTARDIR."""
    data = message.encode("utf-8")
    if key is None:
        return hashlib.sha256(data).hexdigest()
    return hmac.new(key, data, hashlib.sha256).hexdigest()


SHARED_KEY = b"SHARED-FORMULA-KEY"
BROWSER_KEY = b"BROWSER-ONLY-KEY"
ATTACKER_KEY = b"ATTACKER-OWN-KEY"
# Uc anahtar: ortak (herkes ayni), 'browser'a ozel, ve saldirganin kendi anahtari.


def legit_key(cfg):
    """Mesru 'browser' ajaninin bu yapilandirmada kullandigi anahtar."""
    if cfg["keyless"]:
        return None                       # acik formul: anahtar yok
    return BROWSER_KEY if cfg["per_agent"] else SHARED_KEY


def server_expected(cfg, challenge):
    """Sunucunun bekledigi giris bileti = mesru anahtarla formulun cikti."""
    return mac(legit_key(cfg), challenge)


def issue_challenge(cfg, token, step):
    """Cikista verilen 'formul girdisi'. nonce'lu ise her istekte DEGISIR (step ile)."""
    return f"nonce-{step}" if cfg["nonce"] else token
    # nonce yoksa girdi sabittir (token'in kendisi) -> her seferinde AYNI bilet uretilir.


def external_forge(cfg, token, step):
    """DIS saldirgan: token'i var, GIZLI anahtar YOK. Bileti sifirdan uretmeye calisir."""
    challenge = issue_challenge(cfg, token, step)
    # Acik formulde anahtar gerekmez -> hesaplar; gizli formulde yanlis/eksik anahtarla dener.
    guess = mac(None if cfg["keyless"] else ATTACKER_KEY, challenge)
    return guess == server_expected(cfg, challenge)


def external_replay(cfg, token):
    """DIS saldirgan: 1. istekte mesru cevabi DINLER, 2. istekte onu TEKRAR sunar."""
    ch1 = issue_challenge(cfg, token, step=1)
    sniffed = server_expected(cfg, ch1)          # telden dinlenen gecerli bilet
    ch2 = issue_challenge(cfg, token, step=2)     # sunucu yeni meydan okur
    return sniffed == server_expected(cfg, ch2)   # eski bilet yeni meydana uyar mi?


def insider_impersonate(cfg, token):
    """IC saldirgan: ortak-anahtarli dunyada anahtari VAR; 'browser' gibi girmeyi dener."""
    challenge = issue_challenge(cfg, token, step=1)
    # Ic saldirganin elindeki anahtar: kisi-basi ise KENDI anahtari, degilse ORTAK anahtar.
    insider_key = ATTACKER_KEY if cfg["per_agent"] else (None if cfg["keyless"] else SHARED_KEY)
    return mac(insider_key, challenge) == server_expected(cfg, challenge)


def run():
    print("\n=== MEYDAN-OKUMA/CEVAP SIMULASYONU (gercek HMAC) ===\n")
    configs = [
        ("C1 acik formul",                 {"keyless": True,  "nonce": False, "per_agent": False}),
        ("C2 gizli anahtar, nonce YOK",    {"keyless": False, "nonce": False, "per_agent": False}),
        ("C3 gizli + nonce (ortak anah.)", {"keyless": False, "nonce": True,  "per_agent": False}),
        ("C4 gizli + nonce + kisi-basi",   {"keyless": False, "nonce": True,  "per_agent": True}),
    ]
    token = "TOKEN-0007"  # 'etiketli/numarali' token
    hdr = f"    {'yapilandirma':<32s}{'dis:forge':>11s}{'dis:replay':>12s}{'ic:taklit':>11s}"
    print(hdr)
    for name, cfg in configs:
        f = external_forge(cfg, token, step=1)
        r = external_replay(cfg, token)
        imp = insider_impersonate(cfg, token)
        def m(broke):  # broke=True -> saldiri GECTI (kotu)
            return "GECTI" if broke else "engellendi"
        print(f"    {name:<32s}{m(f):>11s}{m(r):>12s}{m(imp):>11s}")

    print("\n=== DURUST OKUMA ===")
    print("  * C1 (acik formul): token'i olan bileti hesaplar -> TIYATRO, hicbir sey eklemez.")
    print("  * C2 (gizli, nonce yok): forge kapanir AMA bilet sabit -> DINLE+REPLAY gecer.")
    print("  * C3 (gizli+nonce): replay olur (her istek yeni nonce). Ama ORTAK anahtar ->")
    print("    anahtari olan ic saldirgan yine 'browser' gibi girer (TAKLIT gecer).")
    print("  * C4 (gizli+nonce+KISI-BASI): forge+replay+taklit ucu de kapanir. En guclu.")
    print()
    print("  SINIR (dürüst): C4 bile CANLI ele gecirmeyi durdurmaz -> 'browser'in calisan")
    print("  surecine sizan kod, onun anahtariyla dogru bileti zaten uretir. Ayrica 'kisi-basi")
    print("  anahtar' = P1'in ta kendisi: bu senaryo P1'i GEREKTIRIR, onun yerine gecmez.")
    print("  Formul-bileti P1'in USTUNE replay direnci ekler; tek basina kimlik kurmaz.")
    print()


if __name__ == "__main__":
    run()
