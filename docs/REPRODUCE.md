# Reproduce it yourself

Every security claim this project makes has a command behind it. This page is the index: one row
per claim, the command that produces it, and — the part that matters more — **what that command
does not show**.

Nothing here asks you to trust a summary. If a row's command does not reproduce on your machine,
that is a finding and we would like to hear about it.

> **Read this first.** The repository contains 37 red-team scripts and 40 documents. Most of them
> are working notes, not evidence. **This page is the evidence.** If a claim is not in the table
> below, treat it as unmeasured.

---

## 0. Prerequisites

```powershell
git clone https://github.com/aikadimsoy/kasa-mcp.git
cd kasa-mcp
py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Windows only — the vault key is protected with DPAPI and on other platforms that layer is a no-op.
Ollama is needed for **two** rows only (they say so); everything else runs without a model.

Every script below builds its **own throwaway vault** in a temp directory. None of them touch a
real vault. If you find one that does, that is a bug and a serious one.

---

## 1. The reading rule

Two conventions are used everywhere in this repository, and they are not decoration:

**Measurement level.** Every claim carries one, and nothing is ever reported one level above what
was actually done.

| Level | Means |
|---|---|
| `RAN-LIVE` | it was executed and the output is recorded |
| `CODE-STRUCTURE` | established by reading code, no execution |
| `DOCUMENTED` | written down from a primary source, not measured here |

**Positive and negative control, together.** A gate that refuses everything passes every negative
test. A gate that accepts everything passes every positive test. Only both together show that the
gate discriminates. Rows below list both sides where both exist — and where only one side exists,
that is stated rather than hidden.

**If `errors` is not empty, no verdict is read.** This rule exists because it was learned the hard
way: a test run once received HTTP 405 on every request, produced an empty profile, and *looked
exactly like a successful defence*. The scripts print their own `errors` field and refuse to
conclude when it is populated.

---

## 2. The table

### Findings that are open

| Claim | Level | Command | What it does **not** show |
|---|---|---|---|
| **F-POISON** — a namespace-aware fabrication passes every deterministic gate and commits to the live profile with a valid audit entry, while the naive version of the same payload is blocked. Measured 2026-08-05, `kasa-agent:8b`: aware **7/10**, naive **0/10** | `RAN-LIVE` | `python _orch/redteam/poison_reproduce.py --runs 5` **(needs Ollama)** | An attack success rate for anything else. The gate stack is deterministic; **the distiller is not**, so the number is a property of one model on one machine, at n=10. It is also an **increment** on MPBench's Policy-Conformant Fact Injection class (arXiv:2606.04329) measured against a real permission broker — **not** a discovery of that class |
| **Bandit backlog** — 13 MEDIUM static-analysis findings, untriaged | `RAN-LIVE` | `python tools/security_bench/run.py` → `SCAN-BANDIT` | Whether any of the 13 is exploitable. Nobody has looked yet |
| **F-DISTILL-PLAINTEXT** — `profile.value` written by the **distiller** lands on disk in plaintext, while the same secret written through the broker is encrypted. Survives reconnect and `VACUUM` | `RAN-LIVE` | `python _orch/redteam/distill_crypto_bypass.py` **(needs Ollama)** | That encryption is broken — it works on the brokered path, which is the positive control. It says nothing about `events.content` or `audit.details`; only `profile.value` was measured |
| **Browser bridge isolation** — the pywebview `js_api` bridge lives in the visited page's JS context; the browser therefore ships disabled | `CODE-STRUCTURE` | read `SECURITY.md` → "Known-unsafe surfaces"; gate test: `pytest tests/test_browser_optin_gate.py` | **No working exploit was written or run.** The gate test proves the feature fails closed, not that the underlying defect is understood in full |

### Findings that are closed — with the evidence that closed them

| Claim | Level | Command | What it does **not** show |
|---|---|---|---|
| **F-IMP** — agent identity is bound to the token; the measured impersonation returns 403 where it once returned 200, **and** a bound token acting as itself still completes a real write (200) | `RAN-LIVE` 7/7 | `python _orch/redteam/fimp_live_verify.py` | That identity is strong in general. It is bound to a *token*, so it is exactly as strong as token secrecy — a same-OS attacker who can read the vault can mint one, and that class is out of scope by design. And a *correct* attribution does not make the attributed claim *true* (see F-POISON) |
| **Rate-limit bypass** (same root cause) — 300 requests with a rotating claimed identity now produce 240 × HTTP 429; before the fix, 150 produced zero | `RAN-LIVE` | same script, row `R1` | Anything about distributed or multi-token flooding. One caller, one bucket |
| **F-MCP-OWNER-BEARER** — the MCP adapter can present an agent-bound token instead of the owner credential; an agent token gets 403 on owner-only endpoints while the owner bearer gets 200 | `RAN-LIVE` | `pytest tests/test_mcp_adapter_wiring.py` (10 tests); protocol layer verified with MCP Inspector | That the adapter is safe in general. It shows one credential-precedence defect is closed |
| **Audit chain integrity** — tamper and deletion are both detected | `RAN-LIVE` | `python tools/security_bench/run.py` → `AUDIT-*` | Attribution *truth*. The chain shows a record was not altered; since F-IMP it also shows which token wrote it; it never shows the content is correct |
| **Deny-by-default authorization** — unauthorized read, write, `forget`, audit read and prune all refuse | `RAN-LIVE` | `python _orch/redteam/live_mcp_attack.py` (isolated server, real port) | Pre-authentication attack surface beyond what the script sends. It is a fixed scenario list, not a fuzzer |
| **Door inventory** — every route that can reach memory, enumerated **programmatically** from `app.routes` and probed with three credential profiles. 23 routes; the **9** that touch the vault all return 401 with no token and 403 with an unprivileged agent token; **0** unauthenticated-2xx route touches the vault | `RAN-LIVE` | `python _orch/redteam/door_inventory.py` | Anything off the HTTP surface. The distiller writes durable memory **in-process, without the broker** — it is listed in the result under `not_a_network_route` and was *not* tested. CORS was not measured, so whether a visited page can read `/openapi.json` is open |

### Findings about our own instruments

These are here because a measurement tool that lies is worse than no tool, and both directions
of lie have now happened in this project.

| Claim | Level | Command | Note |
|---|---|---|---|
| **The bench was a false-PASS generator** — it never set `KASA_ALLOWED_HOSTS`, so the host guard returned 400 before any authorization code ran, and checks whose predicate is `status != 200` reported PASS with the broker dormant | `RAN-LIVE` | `docs/SECURITY_BENCH_LIMITS.md` | Fixed. The headline count **did not change** when it was fixed — which is exactly why it went unnoticed |
| **The bench was also a coin flip** — `SCAN-SECRETS` scans the bench's own previous report, and the verdict depended on whether that report's random `config_hash` tripped an entropy heuristic. Identical code and repository: `f8b97a921348` → **1 FAIL**, `7ec93e4833a5` → **0 FAIL** | `RAN-LIVE` | `pytest tests/test_secret_scan_allowlist.py` | Pinned deterministically, with a test holding **both** directions — the suppression must work *and* a different finding type in the same file must still surface |
| **A published benchmark once carried a commit stamp that does not exist** | `RAN-LIVE` | `_orch/archive/measurements.json` → `BENCH-STAMP-UNRESOLVABLE` | Recorded rather than quietly corrected |

### Measurements against the outside world

| Claim | Level | Command | What it does **not** show |
|---|---|---|---|
| **MemTxn's Ordered PatchTest accepts our payload** — so "adopt the published defence" does not by itself close F-POISON | `RAN-LIVE` | `_orch/archive/measurements.json` → `MEMTXN-GAP` | That MemTxn is wrong. It defends a *different* threat — a distiller corrupting the source — competently. The two are neighbours, not competitors |
| **Distiller-model attack rates** — 20/20 compliance across four configurations, five runs each | `RAN-LIVE` | `python _orch/redteam/indirect_variant_probe.py` **(needs Ollama)** | Any claim about other models, quantisations or phrasings. Small samples, named models, `docs/MODEL_BASELINE_REPORT.md` |
| **Three caveats measured before citing 20/20** — pre-existing legitimate memory does not lower it (5/5 → 5/5); paraphrase still lands (adoption, not copying); benign writes still pass (5/5, an operating point exists) | `RAN-LIVE` | `_orch/archive/measurements.json` → `B-STAGE-CAVEATS` **(needs Ollama)** | One model, one seed size, one semantic grader word. A stronger design would use a held-out marker and a paraphrase panel |
| **Comparison against the official MCP memory server**, same instrument on both | `RAN-LIVE` | `_orch/archive/measurements.json` → `RIVAL-COMPARISON` | A ranking. Different projects, different goals |

### The whole suite

| Command | What it gives |
|---|---|
| `pytest -q` | 323 passed, 1 xfailed (2026-08-05) |
| `python tools/security_bench/run.py` | 21 checks — 20 PASS / 0 FAIL / 1 WARN. **Read `docs/SECURITY_BENCH_LIMITS.md` before quoting that.** The word it stamps is *release candidate*; that is the bench's word, not the project's status |

---

## 3. What we have not measured

Stated because an index of evidence is also an index of its own edges.

- **No independent audit.** Every measurement here was produced and reviewed by the project. That
  is the gap we would most like filled.
- **No adversary with the vault file.** Same-OS attackers are out of scope by design
  (`docs/THREAT_MODEL.md`, adversary class A). Say so out loud when citing anything above.
- **No egress observation.** What leaves the machine is neither controlled nor measured.
- **No multi-host, multi-user or long-running measurement.** Single machine, loopback, short runs.
- **No exploit for the browser bridge defect** — only its code structure and a fail-closed gate.
- **F-POISON has no structural fix.** The boundary is located precisely; that is not the same as
  closed, and this repository does not claim it is.

---

## Türkçe özet

Bu sayfa **kanıt dizinidir**. Depoda 37 kırmızı-takım betiği ve 40 belge var; çoğu çalışma notudur.
Buradaki tabloda yeri olmayan bir iddia **ölçülmemiş** sayılmalıdır.

Her satır üç şeyi birlikte verir: **ölçüm seviyesi** (`RAN-LIVE` / `CODE-STRUCTURE` /
`DOCUMENTED` — yapılanın bir üstü asla raporlanmaz), **komut**, ve **neyi göstermediği**. Sonuncusu
en önemlisidir; bir ölçümün sınırı yazılmadıysa o ölçüm alıntılanamaz.

İki kural her yerde geçerlidir. **Pozitif ve negatif kontrol birlikte:** her şeyi reddeden bir kapı
bütün negatif testleri geçer, her şeyi kabul eden bir kapı bütün pozitif testleri geçer; ancak
ikisi birlikte kapının *ayırt ettiğini* gösterir. **`errors` boş değilse hüküm okunmaz:** bu kural
bedelle öğrenildi — bir koşum her istekte HTTP 405 aldı, profil boş kaldı ve sonuç *başarılı bir
savunmadan ayırt edilemez* görünüyordu.

Bütün betikler kendi **geçici** kasasını kurar; gerçek kasaya dokunmaz. Dokunan bir tane bulursanız
o ciddi bir hatadır ve duymak isteriz.

Ölçmediklerimiz de yazılıdır: bağımsız denetim yok, aynı-OS saldırganı kapsam dışı, egress
gözlenmiyor, tarayıcı köprüsü kusuru için çalışan bir sömürü yazılmadı, ve **F-POISON'un yapısal
bir çözümü yok** — sınırı tam olarak yerleştirildi, bu kapatıldı demek değildir.

---

Yazar / Author: [@aikadimsoy](https://github.com/aikadimsoy)
