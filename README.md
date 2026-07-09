# Project KASA

A Sovereign, Local-First Memory Vault for Agentic Browsing on Windows

## The Problem

Current agentic browsers store persistent user memory in vendor clouds, posing significant privacy and control issues. Users lack ownership of their browsing data, and the legal implications of granting permissions to AI agents are not clearly defined. This project aims to address these shortcomings by providing a local-first, encrypted, user-owned memory vault that can be accessed by any agent via a permission-brokered MCP (Model Context Protocol) server.

## What KASA Does

KASA is designed as a sovereign memory vault for Windows users, ensuring complete control over their browsing data. It operates on the principle of "Agents come and go; your memory is yours." The system includes:

- A local Memory Vault that stores all user data in an encrypted format.
- An MCP Server that exposes this vault to any agent with permission via a brokered protocol.
- Permission calculus ensures that only authorized agents can access the data, maintaining strict control over user information.

## Architecture

KASA's architecture comprises five key components:

| Component | Role | MVP Availability |
|-----------|------|------------------|
| Memory Vault | Encrypted local store for user data | ✅ |
| MCP Server | Localhost server exposing the vault to agents | ✅ |
| Agent Core | Local model and planner | ✅ (distillation only) |
| Permission Broker | Deterministic gate for external access | ✅ (scope checks) |
| Browser Extension | Reads pages, later executes actions | Deferred |

### Design Invariants

1. **Thin Edges, Thick Core**: The extension must contain no intelligence and no data; all state lives in the helper application.
2. **Model is Not the Security Boundary**: Authorization decisions are made by the Permission Broker in ordinary code.
3. **Page Content is Data, Not Instructions**: Any text originating from the web is tagged as quoted data. Goals may be derived only from the user's own commands.

## Security

KASA prioritizes security with several measures in place:

- **Red Team Story**: The project has undergone rigorous testing to identify and mitigate vulnerabilities. Key findings and mitigations include:
  - Prompt injection into the nightly distillation chain was addressed by wrapping all untrusted event text in explicit markers and implementing a QC provenance gate.
  - MCP authorization vulnerabilities were closed through strict allow-lists and deny-lists for agents and tools.
  - Autonomous, zero-cost test->fix loops ensured continuous security improvements with real browser health checks.

## Install & Run

To install and run KASA on Windows:

1. **Dependencies**: Install required Python packages using the following command:
   ```bash
   pip install -r requirements.txt
   ```
2. **Local Ollama Runtime**: Ensure you have a local Ollama runtime running with the `qwen2.5:7b` model at http://localhost:11434.
3. **Configuration**: Copy `kasa.toml.example` to `kasa.toml` and set your desired configurations in it, such as server host/port and vault path.
4. **Start the System Tray App**: Run the application using:
   ```bash
   python run.py
   ```
5. **Headless Mode for MCP Server Only**: For running only the MCP server without the tray icon:
   ```bash
   python run.py --no-tray
   ```
6. **Run One Distillation Pass and Exit**: Use the following command to perform one distillation pass and exit:
   ```bash
   python run.py --distill-now
   ```
7. **Encrypted Portable Export**: Export your vault as an encrypted file with:
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

- MVP-0 security core (vault + MCP server + brokered permissions + distillation + audit hash-chain) is implemented and security-hardened: all security tests are green (prompt-injection, MCP authz C5/C7/C8, browser health gate). Note the honest framing — prompt injection remains an industry-wide open problem; KASA's defense is *structural* (the model is never the security boundary), not a claim of invulnerability.
- Browser extension, web actions (A1-A3), cloud masking/escalation, and the fingerprint-spoofing layer are deferred / parked (out of MVP-0 scope).

## License

License: TBD
