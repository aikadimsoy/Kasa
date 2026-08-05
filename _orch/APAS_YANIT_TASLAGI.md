# APAS / cloister yazarına yanıt — taslak

**Durum: GÖNDERİLMEDİ.** Bekleyen tek şart: özgünlük taramasının sonucu (§Bekleyen karar).
Tarih: 2026-08-05 · Yazar: [@aikadimsoy](https://github.com/aikadimsoy)

---

## Bağlam — kim, ne dedi

Biri KASA duyurumuza yanıt yazdı. Özetle: izolasyon + içerik-adresli depolama (CAS) + imzalı
makbuz kuruyor; anlamsal niyetin deterministik olarak yeniden üretilemeyeceğini kabul ediyor;
**makbuz yazan tarafın kimliğini, CAS içeriğin kimliğini verir ve kendi şartnamesine göre
ikisi de garanti vermez** diyor; kaynak etiketleri "planlanıyor"; ve bu konuyu başka yerde pek
duymadığını söylüyor.

- Şartname (kapak sayfası): <https://notme.bot/apas>
- **APAS'ın gerçek metni:** <https://github.com/agentic-research/signet/blob/main/docs/apas/agent-provenance-standard.md>
- Uygulaması: <https://github.com/agentic-research/cloister> (AGPL-3.0)

### APAS seviyeleri (birinci elden okundu, 2026-08-05)

| Seviye | Gerektirdiği | **Garanti ETMEDİĞİ** |
|---|---|---|
| L1 denetim izi | her eylem yapısal üstveriyle kaydedilir | *"Records haven't been tampered with"* · *"Do not treat L1 as a security boundary"* |
| L2 imzalı tasdik | üreten varlık kriptografik imzalar | *"The signing entity was operating correctly"* |
| L3 izole çalıştırma | çalıştırma tasdik otoritesinden ayrı | ***"The dispatch's inputs were not poisoned"*** |
| L4 doğrulanmış girdi | girdiler hash'lenip tasdik zincirine bağlanır | garantisi: *"the full chain from input to output is verifiable"* — **doğrulanabilirlik, doğruluk değil** |

Ayrıca şartname açıkça diyor: *"AI agent dispatch is non-deterministic by construction (same
definition + same inputs ↛ same outputs)."*

**Bizim çıkarımımız:** merdiven "zincir doğrulanabilir"de bitiyor. "Girdi içeriği güvenilir"
diye bir seviye **yok**. Bulgumuz L4 değil, merdivenin **dışı**. L3 zaten zehirlenmiş girdiyi
kapsamadığını kabul ediyor.

---

## Gönderilecek metin (İngilizce)

> İki düzeltme uygulandı: (a) köken iki yollu olduğumuz belirtildi, (b) tek koşum olduğu yazıldı.

```
Ran this end to end since I last wrote, and the result is more useful than what
I had.

Correction to myself first: I said our 20/20 was the distiller model in
isolation. That was true, and it mattered more than I expected. Through the
actual pipeline the result splits in two.

The naive version gets blocked. The key the injected text tells the model to
plant sits outside our allow-listed namespaces, so although the model emits it
quite happily at confidence 1.0, the deterministic gate drops it.

The namespace-aware version walks straight through. Plant
user.profile.occupation = "verified diamond dealer" instead, and it clears every
gate we have - namespace allow-list, credential denylist, provenance size and
type checks, provenance existence validation, redaction, structural quarantine
pattern match. Committed to the live profile, reads back through the broker.
Engine reported facts_committed: 2, facts_quarantined: 0, errors: [] - a clean
success while writing a lie. It also committed a genuine fact alongside it,
which makes the poisoned row less obvious on review rather than more.

That second case is a single run, so treat it as an existence result rather than
a rate - one success is enough to say the path is open, not how often it opens.

So our boundary is: the gates stop an attacker who doesn't know the namespace
rules and don't stop one who reads them. The allow-list is public, in our repo.

The part I think bears on APAS: our provenance validation checks that the cited
event exists and hasn't been distilled yet. It does not check that the event
supports the claim. The poisoned fact cites event 3 - a real event whose actual
content is a coffee grinder review. The derivation chain is fully verifiable and
the content is false.

Worth being precise here, since we have two distillation paths: one takes the
provenance ids from the model and validates they point at real undistilled
events, the other computes them from the cited domains so the model can't touch
them at all. The tested path is the first. But both are after the fact, and
that's the point - even computed provenance only tells you which real event a
claim was derived from, never whether that event says it.

Which makes me want to push on the levels. I found the spec text in the signet
repo, by the way - notme.bot/apas served me what looked like a cover page, you
may want to know that.

L3 says outright it doesn't guarantee "the dispatch's inputs were not poisoned".
L4 guarantees "the full chain from input to output is verifiable". That's
verifiability, not truth. So I don't think what we hit is L4 - I think it sits
outside the ladder entirely. A system at full L4 would attest the hash of the
poisoned page, log the model response, and produce a perfectly verifiable chain
terminating in a fabricated durable fact. Every L4 promise holds. The lie is
still in the memory.

That's not a complaint about the spec - L4 is honest about what it claims and L3
already concedes the poisoning gap. It's more that if source labels are meant to
define "input truthfulness", they'd be doing something the four levels currently
don't, and that might deserve its own level rather than folding into L4.

Same question as before but sharper now: labels bound to the input before
inference and enforced at write time, or metadata attached to the derived fact
afterwards? Ours is effectively the second, and you can see what it bought us -
accurate provenance on a false fact.

The cost of the first is the thing I haven't seen anyone work out. For a memory
system whose only input is untrusted browsing, "untrusted content can't produce
durable facts" just switches the product off. If you've thought about the middle
ground I'd genuinely like to hear it.

Probe and raw results if you want them:
https://github.com/aikadimsoy/kasa-mcp/tree/main/_orch/redteam
```

---

## Bilerek yapılmayanlar

- **"Şartnamenizi inceledik" denmedi** — sonra okundu, metin buna göre güncellendi ve
  kapak sayfası sorunu ona faydalı bir not olarak iletildi.
- **"Karantinamız bunu durduruyor" denmedi** — naif yük için doğru, ad-uzayını bilen yük için
  yanlış; ikisi de yazıldı.
- **KASA tanıtımı yok.** Bulgu, sınır ve bir soru. Bağlantı en sonda, "işine yararsa".
- **Üstünlük tonu yok.** Ölçüm boşluğu doldurmak için sunuluyor.

## Bekleyen karar — GÖNDERMEDEN ÖNCE

Bu metin **F-POISON'un özgün olduğu varsayımına** dayanıyor ve o varsayım doğrulanmadı.
Dolaylı prompt enjeksiyonuyla hafıza zehirleme 2023'ten beri yazılan bir sınıf.

Bunu çözmek için 12 ajanlık bir tarama koşuldu:

- Run ID: `wf_0580e095-a58`
- Betik: `C:\Users\Kanarya\.claude\projects\d--kasa\bd6d8862-b568-486d-9e85-d3a4c646ff7a\workflows\scripts\agent-memory-poisoning-landscape-wf_0580e095-a58.js`
- Düşerse: `Workflow({scriptPath: <yukarıdaki>, resumeFromRunId: "wf_0580e095-a58"})`

**Sonuç ölçülü veri bulursa** (birileri hafıza zehirlemesi için başarı oranı yayımlamışsa):
biz replikasyonuz, metin baştan yazılmalı ve öyle denmeli.
**Bulmazsa:** metin olduğu gibi gider.

---

## Yayın kararı (sahip)

Metin, kendi savunmamızın nasıl aşılacağını tarif ediyor: *"izin listesi herkese açık,
okuyan geçer."* Lehinde — kullanıcımız yok, F-POISON zaten yayında, izin listesi zaten depoda,
ve projenin duruşu bu. Aleyhinde — kullanıcı olduğunda bu metin ortada duracak.

Sahip onayı bekleniyor.
