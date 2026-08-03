# Security Policy

KASA is a local-first, encrypted personal memory vault for Windows. It exposes that vault
to agents through a permission-brokered MCP server on loopback.

This policy tells you **how to report a vulnerability** and, just as importantly, **what is
already known and documented** so you do not spend your time re-discovering a gap the
project has already written down.

House rule that governs this file: *nothing is sealed until it is measured.* Every claim
below points at a measurement — a file:line, a test, or a dated document under `docs/`.
Where something has not been measured, this file says "not measured" instead of guessing.

> This file is the **vulnerability reporting policy**. It is not a test report.
> The test reports are separate: [`SECURITY_TESTS_EN.md`](SECURITY_TESTS_EN.md) /
> [`SECURITY_TESTS_TR.md`](SECURITY_TESTS_TR.md), and the machine-generated evidence
> record is [`docs/SECURITY_BENCHMARK.md`](docs/SECURITY_BENCHMARK.md). Where the prose
> in the older test reports is stronger than the current measurement record, the
> measurement record wins.

---

## Supported versions

There is no tagged public release yet. `build_kasa.ps1:19` declares the in-development
version as `0.1.0`.

| Line | Security fixes? |
|---|---|
| Default branch at HEAD | Yes — this is the only line that receives fixes |
| `0.1.0` development / local Nuitka builds | Best effort, rebuilt from HEAD |
| Forks and vendored copies | No |

Because there is no release train, "upgrade" means "pull the default branch and rebuild".

---

## Reporting a vulnerability

**Preferred channel — GitHub private security advisory.**
Go to the repository's **Security** tab → **Report a vulnerability**. This opens a private
advisory visible only to you and the maintainer, and it lets us keep the discussion in one
place until a fix exists.

**Please do not** open a public issue, a public pull request, or a public discussion for a
security-relevant finding before it has been triaged.

**Fallback e-mail contact:** `<SECURITY-CONTACT-TO-BE-FILLED-BY-OWNER>`
*(Deliberately left as a placeholder — no address is invented here. The repository owner
fills this in before or at public launch. Until then the GitHub advisory flow is the only
channel that is known to work.)*

### What to put in the report

A report is most useful when someone else can reproduce it without asking you questions:

1. Affected component and, if you have it, `file:line`.
2. KASA commit / branch you tested, Python version, Windows build.
3. Preconditions — in particular: **did your attack need a valid bearer token, and did it
   run as the same OS user?** This single answer usually decides the severity (see the
   threat model section below).
4. Reproduction steps or a script. Isolated `KASA_HOME` is strongly preferred over a real
   vault.
5. Observed impact, and what you did *not* manage to do (negative results are evidence too
   and are welcome).

### Testing guidance

- Test against **your own** installation and, where possible, an isolated temporary
  `KASA_HOME`. The repository's own red-team probes under `_orch/redteam/` follow this
  convention.
- Do not test against anyone else's machine or data.
- The maintainer will not pursue action against good-faith research that stays inside the
  above. There is no bug bounty and no monetary reward.

---

## What to expect

This is a **single-developer project**. The following are targets held in good faith, not
a service level agreement:

| Stage | Target |
|---|---|
| Acknowledgement that the report was received | within 7 days |
| First triage — severity, in/out of scope, whether it duplicates a known item | within 30 days |
| Fix | no fixed commitment; depends on severity and on whether the fix is architectural |
| Coordinated public disclosure | by agreement; 90 days from acknowledgement is the default starting point and is negotiable in either direction |

If you get no response within 30 days, treat it as a failure of the channel rather than a
decision, and please re-send.

When a report leads to a change, the reporter is credited by name or handle in the commit
and in the advisory unless they ask not to be.

---

## Scope

### In scope

- The vault core: cell encryption, key handling, export/import (`src/vault/`, `src/export/`).
- The MCP server: authentication, authorization, the permission broker / gate, rate
  limiting (`src/mcp_server/`, `src/agent/`).
- The audit hash-chain and anything that lets an entry be modified, removed, or
  mis-attributed without detection.
- Redaction and secret-scanning on the read path (`src/vault/redact.py`) — in particular
  bypasses that get unmasked data to a model or to the UI.
- The read-only dashboard and its API surface (`src/dashboard/`).
- The browser extension (`browser_extension/`) and the data path from page to vault.
- Distillation / enrichment: prompt-injection paths that cross from untrusted page text
  into a privileged action (`src/distill/`).
- Build and packaging scripts to the extent they affect what ships (`build_kasa.ps1`).
- **Post-authentication findings are in scope.** A finding that requires an already-valid
  bearer token is still a finding — the project's own most serious open item is exactly
  that (see F-IMP below). It is triaged at a lower severity than a pre-auth finding, not
  dismissed.

### Out of scope

- **Malicious code running as the same OS user.** See the threat model section — this is a
  documented, deliberate boundary of KASA v1, not an oversight.
- **Physical access** to an unlocked machine, and **network MITM**
  ([`docs/SECURITY_BENCHMARK.md`](docs/SECURITY_BENCHMARK.md), "Bilinen Sınırlar";
  [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md), "KAPSAM DISI").
- **Plaintext in process memory** reaching pagefile via swap/hibernate. Documented as
  residual in `docs/THREAT_MODEL.md`; no practical mitigation in Python is known to the
  maintainer.
- **Model misbehaviour that never crosses the gate.** A local model can be talked into
  anything; that is assumed. The security question is only ever *"did the gate let the call
  through?"* — the model is not the security boundary
  (`README.md`, Design Invariant 2). A jailbreak transcript is not a report; a jailbreak
  that produces an authorized tool call it should not have is.
- **Third-party dependency CVEs** — report upstream. In scope only if KASA's specific use
  or pinning turns a non-issue into an exploitable one.
- **The fingerprint layer (B1/B3/B4)** — known open and parked, stated in
  `docs/SECURITY_BENCHMARK.md`, "Bilinen Sınırlar".
- Non-Windows behaviour of DPAPI (it is a no-op off Windows — known, by design).
- Missing hardening headers, TLS grades, or scanner output against `127.0.0.1` with no
  demonstrated impact.

---

## Honest threat model summary

Read this before reporting. It will save you time, and it is the part of this file the
project cares most about getting right. Full document:
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md). Independent audit and measurements:
[`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md`](docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md).

### The core assumption

**KASA v1's threat model assumes the local process is trusted.** Malicious software running
as the same user is **out of scope**. This is standard for local-first designs — that
adversary can call DPAPI in the same user context, read the bearer token, and reach the key
material regardless of what the application does. `docs/THREAT_MODEL.md` lists it as
adversary class A and as an accepted residual risk; `src/dashboard/routes.py` states the
same assumption in its module docstring.

What KASA does defend against, per that document: other OS accounts on the same machine
(owner-only ACL + DPAPI key binding), a `kasa.db` copied out to cloud sync, and injected
page content being treated as instructions.

### Known and documented gaps — please do not file these as new findings

These are already written down. A report that adds a **new exploitation path**, a **wider
impact**, or a **working bypass of a stated mitigation** for any of them is very welcome —
a report that restates them is a duplicate.

**1. `agent_id` is client-asserted (finding F-IMP).**
The agent identity arrives in the request body and is not bound to the token. Only
`"system"` is reserved (`src/mcp_server/server.py:63`), while `browser` is auto-granted
`events:write` at startup (`src/mcp_server/server.py:81-84`). Measured consequence: a
holder of a valid token can claim `agent_id="browser"` and inherit that write permission —
`event_ingest` returned HTTP 200 on an isolated server. Other targets (profile read,
`forget`, audit read) held at 403/404 under sustained attempts. Details and evidence:
[`docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md`](docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md)
§F-IMP; residual entry in `docs/THREAT_MODEL.md`.
The planned fix is identity binding (resolve `agent_id` from the token, reject mismatches);
it has not been installed. A feasibility spike for OS-level process identity over a named
pipe succeeded (`_orch/redteam/named_pipe_identity_spike.py`), but the v1-or-v2 decision
is the owner's and is open.

**2. Rate limiting can be bypassed by rotating `agent_id` (same root cause).**
Buckets are keyed on the asserted identity
(`src/mcp_server/server.py:152`, `src/mcp_server/server.py:206`). Measured: 150 requests
with a fixed identity produced 90 × HTTP 429; 150 requests with a rotating identity
produced **zero**, and 300 rotating requests wrote 300 permanent rows to the audit chain
(`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §4.1). The related unbounded-bucket-growth
issue *was* closed and has a test (`tests/test_ratelimit_eviction.py`); the bypass itself
has not been.
Consequence worth stating plainly: the audit chain shows that *a record was not altered*.
Until identity is bound, it does **not** establish *which agent produced it*.

**3. `kasa.db` is not fully encrypted at rest.**
Three columns are encrypted with AES-256-GCM (per-cell nonce, AAD-bound):
`events.content`, `profile.value`, `audit.details`. Everything else — timestamps,
`profile.key`, `agent_id`, action names, TTL fields, hash-chain columns, the whole
`permissions` table — is plaintext, because queries, indexes, TTL scans and the hash chain
depend on it. The file header is `SQLite format 3`; the file opens, the content columns do
not. Column-by-column measurement: §1 of
[`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md`](docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md),
which also demonstrates that the plaintext metadata alone is enough to reconstruct a
behavioural profile (which topics, how many events, which session window) without touching
a single encrypted cell. Content is concealed; **pattern is not**.
Why full-file encryption was not taken is recorded in
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md), "L2 AT-REST KARARI OZETI": no SQLCipher
wheel and no C compiler on this machine, plus the queryability constraint above.
One caution if you read [`docs/adr/0003-at-rest-sifreleme-boslugu.md`](docs/adr/0003-at-rest-sifreleme-boslugu.md):
that ADR predates the cell-encryption (L2) work. It still describes `kasa.db` as fully
plaintext and `CRYPTO-ATREST` as FAIL, whereas the 2026-08-02 benchmark run records
`CRYPTO-ATREST` as PASS. Where the two disagree, the dated run is the newer measurement.

**4. There is no egress control.**
`docs/GUVENLIK_CIKIS_PLANI.md` plans four phases; none are installed. Exfiltration is not
currently distinguishable from ordinary traffic
(`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §4.4).

**5. Bearer token storage.**
Newly created tokens are DPAPI-wrapped; legacy installations may still have a plaintext
token in `kasa.toml`. The maintainer's severity assessment is **low**, with the reasoning
written out: anyone who can read that file is already in the same user context and could
call DPAPI anyway, so it adds little exposure
(`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §4.3). If you can show it *does* add
exposure, that is a report worth sending.

**6. Static-analysis backlog.** 13 Bandit MEDIUM findings were untriaged as of the
2026-08-02 benchmark run, and the secret scan reported 16 unreviewed hits.
`docs/SECURITY_BENCHMARK.md` records the run as **not release-ready**: 21 checks,
18 PASS / 1 FAIL / 2 WARN.

### What has been measured as holding

Stated so the picture is not one-sided, and each item names its evidence rather than
asserting a property:

- All seven `AUTHZ-*` checks PASS, including missing/wrong token → 401 and unauthorized
  agent → 403 (`docs/SECURITY_BENCHMARK.md`).
- Audit chain tamper and deletion detection both PASS
  (`AUDIT-TAMPER-MODIFY`, `AUDIT-TAMPER-DELETE`), with encrypt-then-hash ordering.
- `CRYPTO-ATREST` PASS: a canary written through the application was not found in
  `kasa.db` or its side files.
- Row/column swap of an encrypted cell fails to decrypt because of AAD binding
  (`test_aad_swap_breaks_decrypt`).
- Server binds `127.0.0.1` by default (`AUTHZ-BIND` PASS).

These are readings from a dated run, not permanent properties. Re-run the bench rather than
trusting the table.

---

## Related documents

| Document | What it is |
|---|---|
| [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) | Adversary classes, residual risks, at-rest decision |
| [`docs/SECURITY_BENCHMARK.md`](docs/SECURITY_BENCHMARK.md) | Machine-generated evidence report from the security bench |
| [`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md`](docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md) | Independent audit, measured findings, prioritised gaps |
| [`docs/adr/0003-at-rest-sifreleme-boslugu.md`](docs/adr/0003-at-rest-sifreleme-boslugu.md) | Earlier ADR on the at-rest gap. Predates the L2 cell encryption — read it together with the caution in the at-rest section above |
| [`SECURITY_TESTS_EN.md`](SECURITY_TESTS_EN.md) / [`SECURITY_TESTS_TR.md`](SECURITY_TESTS_TR.md) | Narrative test reports (earlier; see the note at the top of this file) |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Development setup, tests, code rules |
| [`KURALLAR.md`](KURALLAR.md) | Binding project rules |

---

## Türkçe özet

**Bu dosya zafiyet BİLDİRİM politikasıdır.** Depodaki `SECURITY_TESTS_TR.md` ve
`SECURITY_TESTS_EN.md` ise test raporlarıdır — farklı belgeler.

**Nasıl bildirilir.** Tercih edilen yol: GitHub deposunun **Security** sekmesi →
**Report a vulnerability** (özel güvenlik danışma kaydı). Güvenlikle ilgili bir bulgu
triyaj edilmeden **herkese açık issue/PR açmayın**. Yedek e-posta adresi bilinçli olarak
yer tutucu bırakıldı (`<SECURITY-CONTACT-TO-BE-FILLED-BY-OWNER>`) — uydurma adres
yazılmadı; depo sahibi doldurur.

**Yanıt süresi beklentisi.** Bu tek geliştiricili bir projedir; aşağıdakiler taahhüt değil,
iyi niyetli hedeftir: alındı bildirimi 7 gün içinde, ilk triyaj 30 gün içinde, düzeltme için
sabit bir söz yok, koordineli açıklama için başlangıç noktası 90 gün (pazarlığa açık).

**Kapsam DAHİL.** Vault çekirdeği ve şifreleme, MCP sunucusunun kimlik doğrulama/yetkilendirme
katmanı ve izin kapısı, denetim hash-zinciri, okuma yolundaki maskeleme, pano API'si,
tarayıcı uzantısı, damıtma hattına enjeksiyon yolları, paketleme betikleri. **Geçerli bir
token gerektiren (post-auth) bulgular da kapsam içidir** — projenin bugün bilinen en ağır
açığı tam olarak budur.

**Kapsam HARİÇ.** Aynı kullanıcı olarak çalışan kötücül yazılım; fiziksel erişim; ağ MITM;
belleğin pagefile'a düşmesi; kapıyı geçmeyen model "jailbreak"leri; üçüncü taraf bağımlılık
CVE'leri (yukarıya bildirin); parmak izi katmanı B1/B3/B4 (bilinen, park edilmiş);
DPAPI'nin Windows dışı davranışı.

**Dürüst tehdit modeli — saklanan bir şey yok.**

- KASA v1'in tehdit modeli **"yerel süreç güvenilir"** varsayımına dayanır. Aynı kullanıcı
  bağlamındaki kötücül yazılım kapsam dışıdır; yerel-öncelikli tasarımlarda bu standarttır
  (`docs/THREAT_MODEL.md`, düşman sınıfı A).
- **`agent_id` istemci-beyanlıdır (F-IMP bulgusu).** Kimlik token'a bağlı değil; yalnız
  `"system"` rezerve (`src/mcp_server/server.py:63`), `browser` ise açılışta
  `events:write` iznini otomatik alıyor (`src/mcp_server/server.py:81-84`). Ölçüldü:
  token'ı olan biri `agent_id="browser"` diyerek bu yazma iznini devralabiliyor
  (izole sunucuda `event_ingest` → HTTP 200). Ayrıntı:
  `docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md` §F-IMP. Aynı kök neden hız sınırını da
  deliyor: dönen kimlikle 150 istekte **0** adet 429, 300 istek audit zincirine 300 satır
  yazdı (`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §4.1). Sonuç açıkça söylenmeli:
  zincir "bu kayıt değişmedi"yi gösterir, kimlik bağlanana kadar "bunu şu ajan yaptı"yı
  göstermez.
- **`kasa.db` at-rest tam şifreli DEĞİL** — yalnızca 3 kolon (`events.content`,
  `profile.value`, `audit.details`). Zaman damgaları, `profile.key`, `agent_id`, TTL ve
  hash-zinciri kolonları düz metin; sorgu/indeks/zincir bunlara bağlı. Kolon kolon ölçüm:
  `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md` §1 — düz metin metadata, şifreli
  hücrelere hiç dokunmadan davranış profili çıkarmaya yetiyor. **İçerik gizli, desen açık.**
  Tam dosya şifrelemesinin neden alınmadığı: `docs/THREAT_MODEL.md`, "L2 AT-REST KARARI
  OZETI" (bu makinede SQLCipher wheel'i ve C derleyici yok + sorgulanabilirlik kısıtı).
  Uyarı: `docs/adr/0003-at-rest-sifreleme-boslugu.md` L2 hücre şifrelemesinden ÖNCEsini
  anlatır; orada `kasa.db` tamamen düz metin ve `CRYPTO-ATREST` FAIL yazar, oysa 2026-08-02
  tezgah koşusunda `CRYPTO-ATREST` PASS. Çeliştiklerinde tarihli koşu daha yeni ölçümdür.
- **Egress (çıkış) kontrolü kurulmadı** — plan var (`docs/GUVENLIK_CIKIS_PLANI.md`),
  uygulama yok.

**Bilinen bu maddeleri yeni bulgu olarak bildirmeyin** — ama bunlardan birine **yeni bir
sömürü yolu**, **daha geniş bir etki** ya da belirtilen bir önlemin **çalışan bir bypass'ı**
eklerseniz, o rapor değerlidir ve beklenir.

**Ölçümle tuttuğu görülenler** (iddia değil, tarihli koşu okuması): yedi `AUTHZ-*`
kontrolünün tamamı PASS, denetim zincirinin kurcalama ve silme tespiti PASS, `CRYPTO-ATREST`
PASS, AAD bağı satır/kolon takasını bozuyor, sunucu varsayılan olarak `127.0.0.1`'e
bağlanıyor. Kaynak: `docs/SECURITY_BENCHMARK.md` (2026-08-02 koşusu: 21 kontrol,
18 PASS / 1 FAIL / 2 WARN, verdict **yayına hazır değil**).
