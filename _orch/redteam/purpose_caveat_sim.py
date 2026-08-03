# -*- coding: utf-8 -*-
"""
AMAC-CAVEAT SIMULASYONU — bir KARAR MODELI (gercek sistem degil, tasarim yardimcisi).

SORU (beyin firtinasi): token'a bir "amac" yuklemenin iki yolu var — sunucu-atanmis vs
    ajan-beyanli. Hangisi gercek sinir, hangisi degil? Ayni saldirgani iki moda karsi
    kosturup FARKI olcelim.

MODELLENEN 2 MOD:
  M1 SERVER_ASSIGNED — token'a amac SUNUCU tarafindan MUHURLENIR (ajan degistiremez).
                       Sunucu: istenen eylem token'in amaciyla uyusmuyorsa REDDEDER.
  M2 AGENT_DECLARED  — amaci AJAN beyan eder; token'a bagli DEGIL. Sunucu eylemi hep izin
                       verir, yalniz beyan-ile-eylem UYUSMAZLIGINI isaretler (dedektor).

SALDIRGAN: amac "profile_read" iken eylem "forget" (yani silmeye calisiyor).
  Beklenti: M1 -> REDDEDILIR (forget != profile_read).  M2 -> IZIN + UYUSMAZLIK bayragi.

NOT: Bu bir MANTIK modeli — gercek kripto/vault/ag yok. Amac iki modun saldiri karsisindaki
    davranisini yan yana gormek. (Yerel model taslagi uretti; Claude denetleyip sonlandirdi:
    Turkce-not kurali eklendi, karisik dal duzeltildi, dürüst-okuma bolumu tamamlandi.)
"""

SERVER_ASSIGNED = "SERVER_ASSIGNED"
AGENT_DECLARED = "AGENT_DECLARED"
# Iki mod sabiti; asagidaki 'server_check' davranisi bu moda gore ayrisir.


class Authority:
    """Token uretir. Sunucu-atanmis modda amac token'a MUHURLENIR ve degistirilemez."""

    def issue(self, agent, purpose=None):
        # purpose=None -> ajan-beyanli mod: token amaci tasimaz, amaci istek zamani ajan soyler.
        return {"agent": agent, "purpose": purpose}


def server_check(mode, token, requested_action, declared_purpose=None):
    """Sunucunun kararini dondurur: (karar, uyusmazlik, not).
    Kritik ayrim: amaci KIM belirliyor — sunucu (baglayici) mu, ajan (yalan soyleyebilir) mi?"""
    if mode == SERVER_ASSIGNED:
        # Amac token'da MUHURLU; istenen eylem amaca uymazsa kapi kapanir (caveat = sinir).
        if requested_action != token["purpose"]:
            return "DENY", False, f"amac-caveat: '{requested_action}' != token.amac '{token['purpose']}'"
        return "ALLOW", False, "eylem token amaciyla uyumlu"
    # AGENT_DECLARED: amac token'a bagli DEGIL -> sunucu eylemi durduramaz, yalniz UYUSMAZLIGI gorur.
    mismatch = (declared_purpose != requested_action)
    # mismatch=True: ajan "profile_read yapiyorum" deyip "forget" cagirmis -> niyet-eylem celiskisi.
    note = ("beyan-eylem UYUSMAZLIGI (dedektor tetiklendi)" if mismatch
            else "beyan eylemle tutarli")
    return "ALLOW", mismatch, note


def run():
    print("\n=== AMAC-CAVEAT SIMULASYONU (karar modeli) ===")
    print("    saldirgan: amac='profile_read' AMA eylem='forget' (silme denemesi)\n")
    auth = Authority()
    attacker_action = "forget"
    # Ayni saldirgan, ayni eylem; tek degisen: amaci kim belirliyor.

    # M1 — sunucu-atanmis: token 'profile_read' icin muhurlu, saldirgan 'forget' istiyor.
    tok1 = auth.issue("attacker", purpose="profile_read")
    d1, m1, n1 = server_check(SERVER_ASSIGNED, tok1, attacker_action)
    print(f"[{SERVER_ASSIGNED}]")
    print(f"   karar: {d1}   uyusmazlik: {m1}   ({n1})")

    # M2 — ajan-beyanli: token amacsiz, saldirgan 'profile_read' beyan edip 'forget' yapiyor.
    tok2 = auth.issue("attacker", purpose=None)
    d2, m2, n2 = server_check(AGENT_DECLARED, tok2, attacker_action, declared_purpose="profile_read")
    print(f"[{AGENT_DECLARED}]")
    print(f"   karar: {d2}   uyusmazlik: {m2}   ({n2})")

    print("\n=== DURUST OKUMA ===")
    print("  * SERVER_ASSIGNED amac = GERCEK SINIR: amac token'da muhurlu oldugu icin saldirgan")
    print("    silme eylemini yapamaz (REDDEDILDI). Bu, ikinci bir en-az-yetki eksenidir.")
    print("  * AGENT_DECLARED amac = SINIR DEGIL: ele gecirilmis ajan amaci yalan beyan eder,")
    print("    eylem yine GECER (IZIN). Ama beyan-eylem uyusmazligi bir DEDEKTOR sinyali verir.")
    print("  * Yani 'amaci ajan yanitlasa' fikri guvenlik duvari kurmaz; audit/anomali degeri")
    print("    tasir. Sinir ancak amaci SUNUCU atarsa dogar — bu da once P1'i (kimlik baglama)")
    print("    gerektirir: sunucu, token'in kime ait oldugunu bilmeden ona amac muhurleyemez.")
    print()


if __name__ == "__main__":
    run()
