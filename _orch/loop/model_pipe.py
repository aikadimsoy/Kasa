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


def draft_review(spec, checklist, on_token=None, num_predict=4096) -> str:
    """deepseek taslak -> qwen inceleme -> nihai tam-dosya python. Fix-job cekirdegi.
    `spec` icinde CURRENT dosya icerigi cagiran tarafindan gomulur."""
    draft = call_model(DRAFTER, spec, num_predict=num_predict, on_token=on_token)
    code = extract_python(draft)
    review_prompt = (
        "Review and FIX against the checklist; ensure the required changes are present and nothing "
        "else broke. Output ONLY the complete corrected file in one ```python``` block.\n\n"
        "=== CHECKLIST ===\n" + checklist +
        "\n\n=== DRAFT ===\n```python\n" + code[:13000] + "\n```")
    review = call_model(REVIEWER, review_prompt, num_predict=num_predict, on_token=on_token)
    return extract_python(review)
