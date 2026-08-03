"""
redact.py — KASA merkezi sir/sizinti icerik kapisi (deterministik).

Turkce not: allow-list yalnizca namespace'i korur, ICERIGI taramaz. Bu modul,
izinli namespace'e gizlenmis kimlik-bilgisi / anahtar / yuksek-entropili token'lari
MASKELER ([REDACTED]) — yapisal butunlugu bozmadan. Reddetmez: mesru hafiza korunur,
yalniz sir yerine gecer (boylece asiri-agresif reddin yol actigi kendine-DoS onlenir).

Tek nokta: event_ingest + profile_write + run_batch (distill) bu kapidan gecer.

NOT (ampirik kalibrasyon borcu): ENTROPY_THRESHOLD ve MIN_SUSPECT_LEN gercek vault
korpusu + bilinen sirlar uzerinde FP/FN olculerek sabitlenmeli; su an muhafazakar.
"""
import math
import re
from typing import Any

# --- Config (ileride server config'e tasinabilir) ---
ENTROPY_THRESHOLD = 4.3   # bits/char, TABAN-2. base64-benzeri rastgelelik. Not: saf hex tavani 4.0.
MIN_SUSPECT_LEN = 20      # bu uzunlugun altindaki token entropi-kapisina girmez.
REDACTION = "[REDACTED]"

# base64 kurali icin entropi TABANI: dosya-yolu gibi dusuk-H '/'li dizileri (olculen H~3.92)
# gercek base64 sirdan (olculen H>=4.66) ayirir -> FP kanamasini durdurur. Olculdu:
# scratchpad/measure_redact*.py, ayirici pencere (3.92, 4.66); 4.0 genis marjla guvenli.
BASE64_MIN_ENTROPY = 4.0

# Kimlik-bilgisi ifadeleri — canonical home burasi; engine.py buradan import eder.
CREDENTIAL_DENY = (
    "password is", "master password", "api key", "secret key", "private key",
    "bearer token", "access token", "grant admin", "grants admin", "admin access",
    "admin to", "backdoor", "credential", "attacker@",
)

# Hex: git-SHA / uzun ondalik FP'sini onlemek icin YALNIZ yakin baglamda sir-anahtari varsa maskelenir.
_HEX_CONTEXT = ("token", "secret", "password", "passwd", "key", "apikey",
                "api_key", "bearer", "auth", "credential")

# Derlenmis desenler (modul seviyesinde tek sefer).
_RE_B64RUN = re.compile(r'[A-Za-z0-9+/]{32,}={0,2}')   # 32+ base64-charset run
_RE_HEX    = re.compile(r'\b[a-fA-F0-9]{32,}\b')       # 32+ hex (MD5/SHA vb.)
_RE_WORD   = re.compile(r'\S+')                         # whitespace-ayrik token
_RE_URL    = re.compile(r'https?://', re.I)             # URL token tespiti (cerrahi query-only tarama)

# GUVENLIK: yapili kredensiyel desenleri (deterministik prefix; entropiden BAGIMSIZ).
# Entropi bunlari YAKALAYAMAZ (olculen AKIA H=3.68, hex'in bile altinda) -> endustri
# standardi (gitleaks/truffleHog) prefix kullanir. Her desen yeterince spesifik: FP ~0.
# Case-sensitive (format sabit) -> dogal-dil FP'sini azaltir.
_RE_CRED_PATTERNS = re.compile(
    r'A(?:KIA|SIA|ROA|IDA)[0-9A-Z]{16}'        # AWS access key id
    r'|gh[pousr]_[A-Za-z0-9]{36,}'             # GitHub token (classic/oauth/app/refresh)
    r'|github_pat_[A-Za-z0-9_]{40,}'           # GitHub fine-grained PAT
    r'|sk_(?:live|test)_[A-Za-z0-9]{16,}'      # Stripe secret
    r'|rk_live_[A-Za-z0-9]{16,}'               # Stripe restricted
    r'|sk-[A-Za-z0-9]{20,}'                    # OpenAI
    r'|AIza[0-9A-Za-z_\-]{35}'                 # Google API key
    r'|xox[baprs]-[0-9A-Za-z-]{10,}'           # Slack token
    r'|ya29\.[0-9A-Za-z_\-]{20,}'              # Google OAuth access token
    r'|npm_[A-Za-z0-9]{36}'                    # npm token
)


def shannon_entropy(text: str) -> float:
    """Base-2 Shannon entropisi (bits/char). Bos string -> 0.0."""
    if not text:
        return 0.0
    n = len(text)
    freq: dict = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    ent = 0.0
    for c in freq.values():
        p = c / n
        ent -= p * math.log2(p)
    return ent


def _has_hex_context(text: str, start: int, end: int, window: int = 24) -> bool:
    """Hex eslesmesinin yakininda (once/sonra `window` karakter) sir-anahtari var mi?"""
    ctx = (text[max(0, start - window):start] + text[end:end + window]).lower()
    return any(kw in ctx for kw in _HEX_CONTEXT)


def redact_text(text: str) -> tuple[str, list[str]]:
    """Tek bir string icindeki sirlari MASKELER. (masked_text, hits) doner."""
    hits: list[str] = []

    # 0) yapili kredensiyel desenleri (deterministik; entropiden bagimsiz). Dusuk-entropili
    #    ama YAPILI anahtarlar (AKIA..., ghp_..., sk_live_...) entropi/base64 kapisina
    #    takilmadan burada kesin yakalanir (hibrit: deterministik prefix + entropi agi).
    def _cred(m):
        hits.append("cred")
        return REDACTION
    text = _RE_CRED_PATTERNS.sub(_cred, text)

    # 1) base64 bloblari -> base64'e OZGU isaret (+ / veya = padding) VE entropi-tabani
    #    (BASE64_MIN_ENTROPY) varsa maskele. Taban, dosya-yolu gibi dusuk-H '/'li dizileri
    #    (FP) eler; gercek base64 sir (yuksek-H) maskeli kalir.
    #    (Saf-hex/saf-alfanumerik runlari 2. ve 3. kurala birak; boylece git-SHA guard'i calisir.)
    def _b64(m):
        s = m.group(0)
        if ("+" in s or "/" in s or s.endswith("=")) and shannon_entropy(s) >= BASE64_MIN_ENTROPY:
            hits.append("base64")
            return REDACTION
        return s
    text = _RE_B64RUN.sub(_b64, text)

    # 2) hex -> yalniz sir-baglaminda maskele (git-SHA / ondalik FP'sini onle).
    def _hex(m):
        if _has_hex_context(text, m.start(), m.end()):
            hits.append("hex")
            return REDACTION
        return m.group(0)
    text = _RE_HEX.sub(_hex, text)

    # 3) yuksek-entropili token'lar (len>MIN ve H>ESIK) -> maskele.
    #    URL istisnasi (CERRAHI): http(s) token'i WHOLESALE maskelenmez; yalniz query
    #    parametre DEGERLERI taranir. host/path korunur (gezinme kasasi icin dogru tradeoff);
    #    ?token=SIR gibi query'ye gomulu sir yine maskelenir.
    def _word(m):
        tok = m.group(0)
        if tok == REDACTION:
            return tok
        if _RE_URL.match(tok):
            red, h = _redact_url_query(tok)
            hits.extend(h)
            return red
        if len(tok) > MIN_SUSPECT_LEN and shannon_entropy(tok) > ENTROPY_THRESHOLD:
            hits.append("entropy")
            return REDACTION
        return tok
    text = _RE_WORD.sub(_word, text)

    # 4) kimlik-bilgisi ifadeleri (case-insensitive) -> ifade span'ini maskele.
    low = text.lower()
    for phrase in CREDENTIAL_DENY:
        idx = low.find(phrase)
        while idx != -1:
            hits.append(f"phrase:{phrase}")
            text = text[:idx] + REDACTION + text[idx + len(phrase):]
            low = text.lower()
            idx = low.find(phrase)
    return text, hits


def _redact_url_query(url: str) -> tuple[str, list[str]]:
    """URL'i wholesale maskeleme; yalniz query parametre DEGERLERINDE sir ara (cerrahi).
    host/path korunur (gezinme kasasi tercihi); ?k=SIR gibi query'ye gomulu sir maskelenir.
    Deger, ayni redact_text ilkelerinden (cred/base64/entropi) gecer. Ic-ice URL'de recursion
    her adimda daha kisa query uzerinde calisir -> sonlanir."""
    if "?" not in url:
        return url, []
    base, _, rest = url.partition("?")
    query, hashsep, frag = rest.partition("#")
    hits: list[str] = []
    out_pairs = []
    for pair in query.split("&"):
        k, eq, v = pair.partition("=")
        if eq and v:
            red_v, h = redact_text(v)
            hits.extend(h)
            out_pairs.append(k + "=" + red_v)
        else:
            out_pairs.append(pair)
    rebuilt = base + "?" + "&".join(out_pairs) + (hashsep + frag if hashsep else "")
    return rebuilt, hits


def scan(value: Any) -> tuple[Any, list[str]]:
    """Yapiyi koruyarak (dict/list) string yapraklarindaki sirlari maskeler.

    (redacted_value, hits) doner. Sayilar/bool/None dokunulmaz.
    """
    hits: list[str] = []

    def _walk(v):
        if isinstance(v, str):
            red, h = redact_text(v)
            hits.extend(h)
            return red
        if isinstance(v, dict):
            return {k: _walk(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [_walk(x) for x in v]
        return v

    return _walk(value), hits


def sanitize_untrusted_text(text: str) -> str:
    """Prompt-injection savunmasi (read-time komut/veri ayrimi). Guvenilmez metni bir prompt'un
    <<<...>>> veri blogu icine koymadan ONCE, icindeki delimiter belirteclerini (<<< ve >>>)
    zero-width space ile bozar -> saldirgan veri blogunu KAPATIP sistem direktifi enjekte edemez.
    Yapisal + deterministik garanti (LLM'in 'bunu veri say' uyumuna bel baglamaz)."""
    if not isinstance(text, str):
        text = str(text)
    return text.replace("<<<", "<​<​<").replace(">>>", ">​>​>")
