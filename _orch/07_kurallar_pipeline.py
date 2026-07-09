"""
KURALLAR.md pipeline — deepseek taslak → qwen review → d:/kasa/KURALLAR.md
"""
import json, re, os
import urllib.request

OLLAMA  = "http://localhost:11434/api/generate"
DRAFTER = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
REVIEWER= "qwen2.5-coder:14b"
ORCH    = "d:/kasa/_orch"

def call_model(model, prompt, label):
    print(f"\n[ORCH] {label} ({model})...", flush=True)
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": True,
        "options": {"temperature": 0.1, "num_predict": 2048}
    }).encode()
    req = urllib.request.Request(OLLAMA, data=payload,
                                  headers={"Content-Type": "application/json"})
    buf = []
    with urllib.request.urlopen(req, timeout=300) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line: continue
            try:
                obj = json.loads(line)
                tok = obj.get("response", "")
                buf.append(tok); print(tok, end="", flush=True)
                if obj.get("done"): break
            except: continue
    print(); return "".join(buf)

def save(name, content):
    os.makedirs(ORCH, exist_ok=True)
    path = f"{ORCH}/{name}"
    open(path, "w", encoding="utf-8").write(content)
    print(f"[ORCH] Kaydedildi: {path}")

def extract_md(text):
    m = re.search(r"```markdown\s*\r?\n(.*?)```", text, re.DOTALL)
    if m: return m.group(1)
    m = re.search(r"```\s*\r?\n(.*?)```", text, re.DOTALL)
    if m: return m.group(1)
    return text.strip()

# ── ADIM 1: deepseek-coder taslak ──
DRAFT_PROMPT = """
Copy the following text EXACTLY inside a ```markdown ... ``` block. Do NOT change, add, or remove any content. Do NOT translate. Output ONLY the block.

```markdown
# KURALLAR

## 1. Onay Sistemi (T1)
- Her modül tamamlandığında sunulur; onay olmadan bir sonraki adıma geçilmez.
- Mevcut onaylı içerik izin alınmadan değiştirilemez (yeniden biçimlendirme dahil).

## 2. Sürüm Yönetimi (T2)
- Sürüm numarası öneri: AI tarafından önerilir. Karar: proje sahibi tarafından verilir.
- MVP-0 → V0.2 (okuma uzantısı) → V0.3 (bulut maskeleme) → V0.4 (eylem katmanı A1)

## 3. Müdahale Eşiği (T3)
- AI optimizasyon önerebilir; şema/kapsam değişikliği yalnızca proje sahibi kararıyla.
- Hata tespit edilirse önce bildir, sonra düzelt.

## 4. Güvenlik Sınırları
- İzin kontrolü asla model tarafından yapılmaz; deterministik kod yapar (broker).
- Web içeriği hiçbir zaman komut sayılmaz; yalnızca alıntı veri.
- A3 sınıfı eylemler (parola, ödeme) ajan aracılığıyla asla gerçekleştirilmez.

## 5. Veri Sahipliği
- Ham olaylar: TTL sonrası (7-30 gün) gerçek silme.
- `forget(topic)`: profil + olaylar + audit tombstone — kalıcı garanti.
- Bulut senkronizasyonu MVP-0 kapsamı dışıdır.

## 6. Ajan Özerklik Kademeleri
- T0: yalnızca öneri
- T1: adım adım denetimli
- T2: site-kapsamlı özerk
- T3: açıkça izin verilmiş rutinler
- Yeni kurulum daima T0'dan başlar.

## 7. Denetim Garantisi
- Her vault erişimi audit zincirine yazılır.
- Audit zinciri hash-chain ile korunur; değişiklik tespit edilebilir.

## 8. Bilinen Hata Günlüğü
- Onaylı içerik izinsiz yeniden biçimlendirilmemeli.
- Sürüm onaysız artırılmamalı.
- Proje sahibi niyeti AI optimizasyonuyla geçersiz kılınmamalı.
- Onaylı içerik bağlamdan düşürülmemeli.
```
""".strip()

draft_raw = call_model(DRAFTER, DRAFT_PROMPT, "KURALLAR TASLAK")
save("07_kurallar_draft_raw.txt", draft_raw)
draft_md = extract_md(draft_raw)
save("07_kurallar_draft.md", draft_md)

# ── ADIM 2: qwen2.5-coder review ──
REVIEW_PROMPT = f"""
Review this KURALLAR.md draft for Project KASA.

## Checklist
1. Are all 8 sections present?
2. Is the language consistently Turkish?
3. Are the governance rules accurate and clear?
4. Any missing critical rules from the PROJECT_BRIEF?
5. Formatting clean (proper headers, bullets)?

## Draft
```markdown
{draft_md[:4000]}
```

Output corrected complete ```markdown ... ``` block.
After the block: one-line Turkish summary of changes (or "Değişiklik yok.").
""".strip()

review_raw = call_model(REVIEWER, REVIEW_PROMPT, "KURALLAR REVIEW")
save("07_kurallar_review_raw.txt", review_raw)
final_md = extract_md(review_raw)
save("07_kurallar_final.md", final_md)

# ── ADIM 3: Uygula ──
out = "d:/kasa/KURALLAR.md"
open(out, "w", encoding="utf-8").write(final_md)
print(f"\n[ORCH] {out} yazildi. ({len(final_md)} karakter)")
print("[ORCH] Pipeline 07 tamamlandi.")
