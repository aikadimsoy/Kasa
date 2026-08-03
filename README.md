# Project KASA

A Sovereign, Local-First Memory Vault for Agentic Browsing on Windows

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
  - *Automated test→fix loops* — a zero-cost local-model loop plus browser health gates run the
    checks repeatedly (`_orch/loop/`, `tools/security_bench/`). They raise regression coverage;
    they are not evidence of security by themselves.

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

## License

KASA is **dual-licensed**:

- **AGPL-3.0** — free for individual, educational and research use, and for any use that keeps
  derivative work open under the same terms. The canonical license text is [`LICENSE`](LICENSE).
- **Commercial license** — for organizations that want to build on KASA without releasing their
  derivative work under the AGPL. Terms: [`COMMERCIAL.md`](COMMERCIAL.md).

Attribution to the author stays with the project under both options.
