# ADR-0002 — Güvenlik benchmark'i kanıt mekanizması olarak

## Durum
Kabul edildi

## Bağlam
- Owner, KASA güvenliğini yayım için KANITLAMAK istiyor.
- İddialar yeniden-uretilebilir olmalı; laf/iddia yeterli değil.

## Karar
- `tools/security_bench` harness'i oluşturuldu; çıktısı tarihli `docs/SECURITY_BENCHMARK.md` ve JSON artefakti.
- Dört katman ölçer: authz; crypto+at-rest; audit; statik/bağımlılık/gizli anahtar tarama.
- Verdict kritik-kapı (critical-gated).
- Benchmark ÖLÇER, düzeltmez.

## Sonuçlar
- Yeniden-uretilebilir kanıt artefakti elde edilir.
- Regresyon için temel (baseline) oluşturulur.
- 'Bilinen sınırlar' doğruca belgelenir.
- Ölçüm, remediation'dan (düzeltme) ayrıdır; remediation owner-gated'dır.
