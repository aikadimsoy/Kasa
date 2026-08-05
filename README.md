# Project KASA

A Sovereign, Local-First Memory Vault for Agentic Browsing on Windows

> ## ⚠️ v0.1 — Research Preview / Security Architecture Demo
>
> **This is an experimental prototype. Do not use it for production or for sensitive data.**
>
> It exists to demonstrate and *measure* an architecture — permissions, encryption and audit
> for local AI agents — not to be a finished product. Run it against throwaway data.
>
> **What is actually true today**, each item pointing at its evidence rather than asserting a
> property:
>
> | | |
> |---|---|
> | Runs entirely locally | vault file, key and permission decisions never leave the machine |
> | Encrypts *specific* fields | 3 columns, AES-256-GCM, AAD-bound — **not** the whole database |
> | Limits tool authority in ordinary code | deterministic broker; the model is never the boundary |
> | Keeps a hash-chained audit ledger | tamper and deletion detection both measured PASS |
> | 233 tests pass | 2026-08-03 run, **in an isolated copy** that imports only from itself |
>
> **What is NOT claimed** — these are open, written down, and some are measured failures:
> identity binding (`agent_id` is client-asserted and audit *attribution* is forgeable),
> full at-rest encryption, egress control, and independent security audit. The KASA browser
> ships **disabled** because of a known bridge-isolation defect. The project's own benchmark
> currently records the verdict **not release-ready**.
>
> We publish our own negative results. The open findings are in
> [`SECURITY.md`](SECURITY.md); the failing measurements are in
> [`docs/SECURITY_BENCHMARK.md`](docs/SECURITY_BENCHMARK.md). Start there, not here.

## The Problem

Current agentic browsers store persistent user memory in vendor clouds, posing significant privacy and control issues. Users lack ownership of their browsing data, and the legal implications of granting permissions to AI agents are not clearly defined. This project aims to address these shortcomings by providing a local-first, encrypted, user-owned memory vault that can be accessed by any agent via a permission-brokered MCP (Model Context Protocol) server.

## What KASA Does

KASA is designed as a sovereign memory vault for Windows users: the vault file, the encryption key and the permission decisions all stay on the user's machine. *Complete* control is **not** claimed — the measured limits (client-asserted `agent_id`, unobserved egress, plain-text metadata columns) are named under Project Status below. It operates on the principle of "Agents come and go; your memory is yours." The system includes:

- A local Memory Vault that encrypts sensitive cells at rest with per-cell AES-256-GCM. Honest scope: encryption is cell-level over three columns, not whole-database — see Project Status below.
- An MCP Server that exposes this vault to any agent with permission via a brokered protocol.
- Permission calculus ensures that only authorized agents can access the data, maintaining strict control over user information.

## Architecture

KASA's architecture comprises five key components:

| Component | Role | MVP Availability |
|-----------|------|------------------|
| Memory Vault | Local store; sensitive cells encrypted (AES-256-GCM), metadata columns plain text | ✅ |
| MCP Server | Localhost server exposing the vault to agents | ✅ |
| Agent Core | Local model and planner | ✅ (distillation only) |
| Permission Broker | Deterministic gate for external access | ✅ (scope checks) |
| Browser Extension | Reads pages, later executes actions | Deferred |

### Design Invariants

1. **Thin Edges, Thick Core**: The extension must contain no intelligence and no data; all state lives in the helper application.
2. **Model is Not the Security Boundary**: Authorization decisions are made by the Permission Broker in ordinary code.
3. **Page Content is Data, Not Instructions**: Any text originating from the web is tagged as quoted data. Goals may be derived only from the user's own commands.

## Security

Every security claim in this repository is expected to name the measurement it rests on. The current
evidence report is [`docs/SECURITY_BENCHMARK.md`](docs/SECURITY_BENCHMARK.md) (21 checks with
per-check evidence strings), the per-test detail with explicit limits is
[`SECURITY_TESTS_EN.md`](SECURITY_TESTS_EN.md), and an independent audit with open findings is
[`docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md`](docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md).

- **Red-team findings — what was measured, and what is still open.** Each line names its evidence;
  nothing here claims the class of attack is solved.
  - *Indirect prompt injection into the distillation chain* — untrusted event text is wrapped in
    explicit delimiters and a QC provenance gate rejects facts the model cannot cite. Measured:
    `tests/test_distill_injection.py`, `tests/test_delimiter_breakout.py`,
    `tests/test_semantic_injection.py`. **Limit:** prompt injection is an industry-wide open
    problem; the defense here is *structural* (the model is never the security boundary), not a
    claim of immunity.
  - *MCP authorization* — the allow-list (`PUBLIC_TOOLS`), reserved-agent block and per-scope
    deny-by-default checks pass their measurements (`AUTHZ-*` checks in
    [`docs/SECURITY_BENCHMARK.md`](docs/SECURITY_BENCHMARK.md); `tests/test_agent_gate.py`).
    **Still open:** `agent_id` is client-asserted, so a token holder can impersonate another
    privileged agent id and audit attribution is forgeable — see the F-IMP finding in
    [`SECURITY.md`](SECURITY.md) and
    [`docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md`](docs/MCP_CANLI_TEST_EYLEM_PLANI_2026-08-02.md).
    This is **not** closed.
  - *KASA browser bridge isolation* — **open, and the reason the browser ships disabled.** The
    pywebview `js_api` bridge lives in the visited page's JS context and page scripts are
    injected with no origin check, so any visited site can reach `window.pywebview.api.*`,
    including `set_proxy()` and `ingest()`. `open_browser()` now refuses to start without
    `KASA_ENABLE_BROWSER=1`, failing closed before any side effect
    (`tests/test_browser_optin_gate.py`, with both a negative and a positive control).
    **Limit:** established from code structure and from the ingest feature's own operation;
    **no working exploit was written or run.** Full write-up: [`SECURITY.md`](SECURITY.md),
    "Known-unsafe surfaces". A smaller defect on the same surface *was* fixed — the address
    bar no longer interpolates the URL into HTML.
  - *Automated test→fix loops* — a zero-cost local-model loop plus browser health gates run the
    checks repeatedly (`_orch/loop/`, `tools/security_bench/`). They raise regression coverage;
    they are not evidence of security by themselves.

### Roadmap

Ordered by what blocks the next honest claim, not by effort. Each item closes a gap that is
currently measured open — the evidence is linked from [`SECURITY.md`](SECURITY.md).

| Version | Goal | Closes |
|---|---|---|
| **v0.1** *(this release)* | Clean public repo, safe example config, limits stated plainly | — |
| **v0.2** | **Verified process/agent identity** — resolve `agent_id` from the token, reject mismatches | F-IMP; makes audit *attribution* meaningful, and fixes the rate-limit bypass that shares its root cause |
| **v0.3** | **Default-deny egress + capability permissions** | "no egress control" |
| **v0.3** | **Privileged UI outside page context** | the browser bridge isolation defect above |
| **v0.4** | Attack testing, brakes and budgets | turns the red-team scripts into gates |
| **v1.0** | Production candidate — *after* independent security review | "no independent audit" |

## Install & Run

### Requirements

- **Windows only.** KASA is not cross-platform today: the tray app uses PyQt5 on Windows, and the vault key is protected with the **Windows DPAPI**. On macOS/Linux the DPAPI layer is a no-op, so the key protection KASA relies on does not exist there (measured limit: `docs/SECURITY_BENCHMARK.md` → "Bilinen Sınırlar" / Known Limits, *non-Windows DPAPI no-op*).
- **Python 3.12 — always use it.** The desktop path is pinned to 3.12: a Nuitka-compiled binary **segfaults** when opening the pywebview window under Python 3.14. This is measured, not assumed — `docs/EXE_PACKAGING_LOG.md`, "Spike-2 Py3.14: SEGFAULT (exit 3)", and the build script refuses any other version at `build_kasa.ps1:29-32`. Honest scope of that measurement: it was observed on the desktop/exe path; the test suite and the security benchmark themselves were last run under 3.14.5 (`docs/SECURITY_BENCHMARK.md` header). Using 3.12 avoids the question entirely.
- **Ollama installed separately.** KASA does not ship or install a model runtime. Distillation is optional at runtime; the vault and the dashboard work without it.

### Steps

1. **Create a virtual environment** (recommended, and it keeps the 3.12 pin explicit):
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. **Dependencies**: Install required Python packages using the following command:
   ```bash
   pip install -r requirements.txt
   ```
3. **Local Ollama Runtime** (optional, needed only for distillation): install Ollama separately from https://ollama.com, then pull the model and make sure it serves at http://localhost:11434:
   ```bash
   ollama pull qwen2.5:7b
   ```
4. **Configuration**: Copy `kasa.toml.example` to `kasa.toml` and set your desired configurations in it, such as server host/port and vault path. The bearer token is generated on first run.
5. **Start the System Tray App**: Run the application using:
   ```bash
   python run.py
   ```
6. **Headless Mode for MCP Server Only**: For running only the MCP server without the tray icon:
   ```bash
   python run.py --no-tray
   ```
7. **Run One Distillation Pass and Exit**: Use the following command to perform one distillation pass and exit:
   ```bash
   python run.py --distill-now
   ```
8. **Encrypted Portable Export**: Export your vault as an encrypted file with:
   ```bash
   python run.py export --output my_vault.kasa --verify
   ```

## MCP Tools

KASA exposes the following MCP tools for local use:

- `profile_read(scope)`, `profile_write(fact)`, `forget(topic)`, `audit_read(range)`, `event_ingest`, `prune_expired_events`.

## Testing

KASA uses pytest for testing. To run the tests, use:
```bash
pytest -q
```

## Project Status

**Not release-ready — and the project says so itself.** The current benchmark stamp reads
**"NOT READY FOR RELEASE"**: 21 checks, **18 PASS · 1 FAIL · 2 WARN**
(`docs/SECURITY_BENCHMARK.md`, commit `2dfda9e`). The house rule is *nothing is sealed until it is
measured*, so labels such as "hardened", "enterprise-grade" or "production-ready" are not used here —
`docs/UI_UX_STANDARD.md` §2.6 forbids them until they are empirically measured.

- **Implemented and measured green:** the MVP-0 security core — vault + MCP server + brokered
  permissions + distillation + audit hash-chain. All 7 `AUTHZ-*` checks pass (including C5/C7/C8 and
  the `127.0.0.1` bind check), the 3 `AUDIT-*` chain/tamper checks pass, the 5 `CRYPTO-*` checks pass,
  both `FUZZ-*` checks pass, and the dependency audit reports 0 vulnerable dependencies.
- **Measured red / amber:** `SCAN-SECRETS` **FAIL** — the bearer token is stored in plain text in
  `kasa.toml`; an owner-only ACL is applied, rotation and DPAPI wrapping are still pending.
  `SCAN-BANDIT` WARN (13 medium findings, untriaged) and `SCAN-BAK-HYGIENE` WARN.
- **Named open gaps**, measured in `docs/KASA_DENETIM_VE_PROJEKSIYON_2026-08-01.md`:
  (a) `agent_id` is client-asserted and unverified, so the rate limiter can be bypassed and **audit
  attribution is forgeable** (§4.1); (b) **egress is neither controlled nor observed** — the plan in
  `docs/GUVENLIK_CIKIS_PLANI.md` is unbuilt (§4.4); (c) at-rest encryption is **cell-level over three
  columns**, not whole-database — metadata columns remain plain text (§1 and
  `docs/adr/0003-at-rest-sifreleme-boslugu.md`).
- **On prompt injection — the honest framing:** it remains an industry-wide open problem class.
  KASA's defense is *structural* (the model is never the security boundary; the permission gate is
  ordinary deterministic code), not a claim of invulnerability.
- Browser extension, web actions (A1-A3), cloud masking/escalation, and the fingerprint-spoofing layer
  are deferred / parked (out of MVP-0 scope).

Test-by-test detail, including what each claim does *not* prove, is in
[`SECURITY_TESTS_EN.md`](SECURITY_TESTS_EN.md).

## Contact

All project contact runs through GitHub. There is deliberately no e-mail address: keeping the
conversation on the repository means it stays public, attributable and searchable by the next
person with the same question, and it does not require the maintainer to publish an address that
would then be permanently indexed.

| What you have | Where it goes |
|---|---|
| A security vulnerability | **Security tab → Report a vulnerability** (private advisory). Read the known-gaps list in [`SECURITY.md`](SECURITY.md) first — it will tell you whether the finding is already documented. |
| A question, an idea, a critique of the architecture or the measurements | [Discussions](https://github.com/aikadimsoy/kasa-mcp/discussions) |
| A reproducible bug that is not security-relevant | [Issues](https://github.com/aikadimsoy/kasa-mcp/issues) |
| A patch | A pull request. Note the dual licence below before you send one. |

Please do **not** open a public issue, pull request or discussion for a security-relevant finding
before it has been triaged.

This is a research preview maintained by one person. Expect considered replies rather than fast
ones, and expect "we measured that and it failed" to be a normal answer.

## License

KASA is **dual-licensed**:

- **AGPL-3.0** — free for individual, educational and research use, and for any use that keeps
  derivative work open under the same terms. The canonical license text is [`LICENSE`](LICENSE).
- **Commercial license** — for organizations that want to build on KASA without releasing their
  derivative work under the AGPL. Terms: [`COMMERCIAL.md`](COMMERCIAL.md).

Attribution to the author stays with the project under both options.

---

**KASA** — a sovereign, local-first memory vault for agentic browsing.
Author: [@aikadimsoy](https://github.com/aikadimsoy) · Repository: <https://github.com/aikadimsoy/kasa-mcp>
