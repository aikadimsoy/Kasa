# -*- coding: utf-8 -*-
"""
KASA loop — ortak yerel-model yardimcisi (SIFIR-TOKEN).
deepseek taslak -> qwen inceleme -> python blok cikar. Mevcut _orch/*_pipeline.py
desenlerinin tek kaynaga cekilmis hali; loop_runner ve tum fix-job'lar bunu kullanir.
Tum uretim http://localhost:11434 uzerinden yerel modellerle yapilir; Claude token harcamaz.
"""
import json, re, urllib.request

OLLAMA   = "http://localhost:11434/api/generate"
PING     = "http://localhost:11434/"
DRAFTER  = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER = "qwen2.5-coder:14b"


def ollama_up() -> bool:
    """Yerel model runtime ayakta mi?"""
    try:
        with urllib.request.urlopen(PING, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def call_model(model, prompt, num_predict=4096, temp=0.15, on_token=None, timeout=1800) -> str:
    """Tek model cagrisi (stream). on_token(tok) verilirse canli akitir."""
    payload = json.dumps({"model": model, "prompt": prompt, "stream": True,
                          "options": {"temperature": temp, "num_predict": num_predict,
                                      "num_ctx": 24576}}).encode()
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    buf = []
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            tok = obj.get("response", "")
            buf.append(tok)
            if on_token:
                on_token(tok)
            if obj.get("done"):
                break
    return "".join(buf)


def extract_python(text: str) -> str:
    """```python ...``` blogunu cikar; yoksa ham metni dondur."""
    m = re.search(r"```python\s*\r?\n(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip() + "\n"


def extract_edits(text: str) -> list:
    """Model cevabindan duzenleme listesini cikarir: [{"old": ..., "new": ...}, ...]

    Once ```json blogu aranir; yoksa metindeki ilk dengeli [ ... ] dizisi denenir.
    Ayristirilamazsa BOS liste doner -> cagiran taraf bunu basarisizlik sayar
    (sessizce "degisiklik yok" diye gecmemeli)."""
    block = re.search(r"```(?:json)?\s*\r?\n(\[.*?\])\s*```", text, re.DOTALL)
    raw = block.group(1) if block else None
    if raw is None:
        start = text.find("[")
        if start == -1:
            return []
        depth, end = 0, -1
        for i in range(start, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            return []
        raw = text[start:end]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict) and ("start" in d or "old" in d) and "new" in d]


_PATCH_RULES = """
RESPONSE FORMAT - THIS IS THE MOST IMPORTANT PART OF YOUR TASK:

Do NOT rewrite the file. The file below is shown with LINE NUMBERS in the form
"  42| code". Output a JSON array of line-range edits instead:

```json
[
  {"start": 42, "end": 42, "old": "the current text of line 42",
   "new": "the replacement text"},
  {"start": 90, "end": 92, "old": "current text of lines 90-92",
   "new": "replacement spanning any number of lines"}
]
```

Hard rules for every edit:
- "start" and "end" are line numbers read from the listing. Use start == end for a
  single line. The line numbers and the "| " separator are NOT part of the file: never
  include them in "old" or "new".
- "old" is the current content of those lines, used as a safety check. Copy it as
  closely as you can; leading indentation matters but trailing spaces do not.
- "new" is the full replacement for that line range, WITH its correct indentation.
- Ranges must not overlap.
- Keep each edit as small as possible: only the lines that actually change.
- Everything you do not list stays byte-identical. You therefore MUST NOT reproduce
  comments, docstrings or unrelated code - they are preserved automatically.
- Output the JSON array and nothing else.
"""


def draft_review_patch(spec, checklist, current, num_predict=2048, on_token=None) -> list:
    """Yama kipi: tam dosya yerine cerrahi duzenleme listesi uretir (taslak -> inceleme).

    SEBEP (2026-08-02, olculdu): tam-dosya yeniden uretiminde model 334 satirlik bir dosyayi
    ALTI dize degistirmek icin bastan yaziyor ve her seferinde uzun Turkce gerekce notlarini
    dusuruyordu (31 aciklama satiri -> 16, ust uste uc turda AYNI sayi). Guard kaybi
    yakaliyordu ama uretmesini engelleyemiyordu; her tur ~20 dakika bosa gidiyordu.
    SONUC: bu kipte model yalnizca DEGISECEK parcalari soyler; dokunmadigi her bayt
    aynen korunur -> yorum kaybi TASARIM GEREGI imkansiz. Ayrica cikti 5000 token yerine
    ~200 token oldugu icin tur suresi dakikalara duser."""
    from guard import number_lines
    listing = number_lines(current)
    # Dosya SATIR NUMARALI gosterilir; model metni tekrar etmek yerine numara secer.
    prompt = (spec + _PATCH_RULES
              + "\n=== FILE (numbered; the \"NN| \" prefix is not part of the file) ===\n"
              + listing + "\n")
    draft = call_model(DRAFTER, prompt, num_predict=num_predict, on_token=on_token)
    edits = extract_edits(draft)
    review_prompt = (
        "You are reviewing proposed line-range edits to a Python file.\n"
        "Check them against the checklist. Fix wrong line numbers, wrong indentation, "
        "overlapping ranges, missing edits or extra edits.\n\n"
        "=== CHECKLIST ===\n" + checklist +
        "\n\n=== PROPOSED EDITS ===\n```json\n" + json.dumps(edits, ensure_ascii=False, indent=2) +
        "\n```\n\n=== FILE (numbered) ===\n" + listing + "\n" + _PATCH_RULES)
    review = call_model(REVIEWER, review_prompt, num_predict=num_predict, on_token=on_token)
    return extract_edits(review) or edits


def draft_review(spec, checklist, on_token=None, num_predict=4096, max_review_chars=13000) -> str:
    """deepseek taslak -> qwen inceleme -> nihai tam-dosya python. Fix-job cekirdegi.
    `spec` icinde CURRENT dosya icerigi cagiran tarafindan gomulur.

    SEBEP (2026-08-01): iki sabit, BUYUK dosyalarda sessiz kirpma uretiyordu —
      (a) num_predict=4096 sabitti; ~5000 token'lik bir dosya (orn. checks/scan.py, 16 KB)
          tam yazilamiyordu -> model dosyayi yarida birakiyordu;
      (b) inceleyiciye giden taslak code[:13000] ile kirpiliyordu -> qwen dosyanin SONUNU
          hic gormeden "tam dosya" uretmeye calisiyordu.
    SONUC (fixlenmezse): guard needle'lari eksik cikti reddeder, is 5 tur boyunca doner ve
    'blocked' olur; kok-neden ise model yetenegi DEGIL, motorun butcesidir -> yanlis teshis.
    KARAR: ikisi de is-basina parametre; varsayilanlar degismedi (mevcut isler etkilenmez)."""
    draft = call_model(DRAFTER, spec, num_predict=num_predict, on_token=on_token)
    code = extract_python(draft)
    review_prompt = (
        "Review and FIX against the checklist; ensure the required changes are present and nothing "
        "else broke. Output ONLY the complete corrected file in one ```python``` block.\n\n"
        "=== CHECKLIST ===\n" + checklist +
        "\n\n=== DRAFT ===\n```python\n" + code[:max_review_chars] + "\n```")
    review = call_model(REVIEWER, review_prompt, num_predict=num_predict, on_token=on_token)
    return extract_python(review)
