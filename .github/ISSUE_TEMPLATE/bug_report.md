---
name: Bug report
about: Report something that is broken or behaves incorrectly
title: "[bug] "
labels: bug
---

> **Stop if this is a security vulnerability.** Do not report it here — this tracker is
> public. Use the repository's **Security** tab → **Report a vulnerability** (private
> advisory). The full policy, including what is already known and documented, is in
> [`SECURITY.md`](../SECURITY.md). Contributor rules: [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## What happened

<!-- One or two sentences. What did you observe? -->

## What you expected

<!-- What should have happened instead? -->

## Steps to reproduce

1.
2.
3.

## Environment (please fill in — KASA is Windows-only)

| Field | Value |
|---|---|
| Windows version (`winver`) | e.g. Windows 11 Pro 24H2 (build 26100) |
| Python version (`python -V`) | e.g. 3.12.7 |
| Ollama model in use | e.g. qwen2.5:7b / hermes3:8b / none |
| Ollama reachable at http://localhost:11434 ? | yes / no |
| KASA start mode | `python run.py` / `--no-tray` / KASA.exe (Nuitka build) |
| KASA version or commit | e.g. 0.1.0 / short git SHA |

## Logs / audit evidence

<!--
Paste the relevant error output. If it is a permission or MCP error, the audit
table is usually the most useful evidence.
REDACT FIRST: never paste your bearer_token (kasa.toml), vault contents, or any
personal facts stored in the vault. This tracker is public.
-->

```
(paste here)
```

---

<!-- TR-NOT (ogretici, .md oldugu icin tam Turkce serbest):
Bu sablon Ingilizce; depo uluslararasi katkiya acik. Turkce yazmak isteyen
katkici Turkce de yazabilir — anlasilirlik onemli, dil degil.
ONEMLI: Hata bildirirken bearer_token, vault icerigi veya kisisel veri PAYLASMA;
bu izleyici herkese aciktir. Ayrica "guvenli/kirilamaz" gibi degil, GOZLEM yaz:
ne yaptin, ne bekledin, ne oldu. -->
