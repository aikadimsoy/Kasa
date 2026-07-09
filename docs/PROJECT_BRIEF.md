# Project KASA — A Sovereign, Local-First Memory Vault for Agentic Browsing on Windows

**Document type:** Project brief and architectural specification (AI-to-AI handoff)
**Origin:** Co-designed by Erhan (project owner) and Claude (Anthropic) in an extended design dialogue, 2026-07-02
**Status:** Draft V0.1 (version *proposed* by Claude; final version numbers are *declared* by the owner — see §10)
**Intended reader:** A coding-capable AI assistant (e.g., Claude Code in VS Code) that will implement MVP-0 under the governance rules in §10

---

## Abstract

Agentic browsers (OpenAI Atlas, Perplexity Comet, Google Gemini auto-browse, Microsoft Edge Copilot) are rapidly becoming the dominant interaction surface of the web. Their competitive moat is not the browser shell — it is **persistent, cross-session user memory**, which today resides exclusively in vendor clouds. This project inverts that ownership model: it specifies a **local-first, encrypted, user-owned memory vault** running on the user's Windows machine, exposed to *any* agent (cloud or local) through a permission-brokered MCP (Model Context Protocol) server. The browser becomes commodity; the memory remains the user's property. The design is grounded in a conditional-entropy storage principle (§3), a deny-by-default permission calculus (§6), and a trust-tiered autonomy model (§7). MVP-0 deliberately excludes all web *actions* and any browser extension, because the action layer carries ~90% of the security and legal risk while the vault alone already delivers standalone value (memory portability across existing assistants).

---

## 1. Problem Statement

Three converging observations motivate this project:

1. **Memory is the prize, not the browser.** The decisive advantage of current agentic browsers is continuity: an assistant that already knows the user's preferences, history, and context. This memory is (a) stored in vendor clouds, (b) non-portable between vendors, and (c) deletable only on the vendor's terms. The user's behavioral profile has become a vendor asset.

2. **The privacy/capability matrix has an empty cell.** As of mid-2026, privacy-focused browsers (e.g., Brave Leo with local models) offer *no* agentic capability, while agentic browsers (Atlas, Comet) are cloud-first. The combination **fully agentic + fully local + user-owned data** is essentially unoccupied by major vendors.

3. **The legal ground is shifting toward explicit authorization.** A 2026 U.S. federal preliminary injunction (Amazon v. Perplexity context) established that a user's permission to an AI agent does not substitute for platform authorization. Architectures must therefore encode the distinction between what an agent *can* do and what it is *permitted* to do — in code, outside the model.

**Thesis:** Build the neutral layer every agent must visit — a sovereign memory vault — rather than another combatant in the browser war.

---

## 2. Positioning and Honest Market Assessment (Designer's Perspective)

This section records the designing AI's candid assessment, so the implementing AI inherits calibrated expectations rather than hype.

- Building a full browser (Chromium fork) is assessed at **~2–3%** probability of sustainable market position for a small team — distribution against Chrome/OS-level integration is prohibitive.
- Building the **vault + MCP layer** (this project) is assessed at **~15–20%** probability of becoming a sustainable niche product, with materially higher option value: even in the failure mode, the artifact remains useful as (a) personal infrastructure, (b) an open-source credibility asset, and (c) a component of the owner's broader KisiselAsistan multi-agent system.
- The strategic claim that survives scrutiny: *"Agents come and go; your memory is yours."* Data-sovereignty demand is strongest in the DACH region (GDPR culture, cloud-averse Mittelstand), which matches the owner's location and prior compliance-oriented work.
- Known headwinds, stated plainly: prompt injection remains the dominant unsolved attack class for agentic systems; platform operators are actively gating third-party agents (legal + technical); local models trail frontier cloud models in complex reasoning, mandating a hybrid design with strict data minimization.

---

## 3. Theoretical Foundation — The Weighting Formulae

The design reuses a single information-theoretic principle across the system, plus two decision calculi. These are the "weight formulas" governing all components.

### 3.1 Conditional-entropy storage principle

```
Store(D) ≈ H(D | M)
```

where `D` is the data to be retained and `M` is a shared model. One never stores raw data; one stores only the *residual* of the data given a shared model, and enriches `M` over time. There is no shortcut past the entropy bound; the only lever is growing `M`.

**Application in this project:** raw browsing/interaction events are the high-entropy stream `D`; the local LLM plus the distillation schema constitute `M`. The vault persists only the **distilled profile** `D|M` (compact, human-readable facts such as "prefers aisle seats", "orders after 20:00") and discards raw events after a short TTL. Storage stays small, meaningful, and auditable — and deletion of a fact is genuine deletion, because no raw shadow copy survives.

### 3.2 Confidence-calibrated escalation (local↔cloud routing)

```
route(task) = local            if conf_local(task) ≥ θ
            = cloud(mask(ctx)) otherwise
```

The local model (7–14B class) handles routine work (summarization, intent parsing, profile distillation). Only when its calibrated confidence falls below threshold `θ` does the system escalate — and then only a **masked** context leaves the device: named entities are pseudonymized locally (`"Erhan" → USER_1`), the cloud answer is de-masked on return. Cloud use is optional; a strictly-local mode must always remain functional. (This continues the owner's prior work on adaptive LLM routing with calibrated confidence and escalation chains.)

### 3.3 Permission calculus (deny-by-default)

```
allow(agent, scope, action_class) =
    granted(agent, scope) ∧ tier(user, site) ≥ required_tier(action_class)
```

evaluated by deterministic code (**never** by the model), with `deny` as the default for every undefined case. Scopes and action classes are defined in §6; autonomy tiers in §7.

---

## 4. System Architecture

Five components; only the first two exist in MVP-0.

| # | Component | Role | MVP-0 |
|---|-----------|------|-------|
| 1 | **Memory Vault** | Encrypted local store: events, distilled profile, permissions, audit log | ✅ |
| 2 | **MCP Server** | Localhost server exposing the vault to agents via scoped tools | ✅ |
| 3 | **Agent Core** | Local model (Ollama) + planner; runs distillation jobs | ✅ (distillation only) |
| 4 | **Permission Broker** | Deterministic gate; every external access passes through it | ✅ (scope checks) |
| 5 | **Browser Extension** ("eyes and hands") | Reads pages, later executes actions; deliberately *dumb* | ❌ deferred |

**Design invariant 1 — thin edges, thick core:** the extension must contain no intelligence and no data; all state lives in the helper application. Switching browsers means attaching a new "hand"; brain and memory persist.

**Design invariant 2 — the model is never the security boundary:** authorization decisions are made by the Permission Broker in ordinary code. The model proposes; the broker disposes.

**Design invariant 3 — page content is data, not instructions:** any text originating from the web is tagged as quoted data. Goals may be derived only from the user's own commands — the structural defense against prompt injection.

---

## 5. Windows-Specific Engineering Decisions

| Concern | Decision | Rationale |
|---|---|---|
| Helper app | **Python + PyQt6** system-tray application | Owner has shipped a ~9-iteration PyQt6 desktop app previously; PoC velocity outweighs Rust/Tauri elegance at this stage. Revisit for production. |
| Vault storage | **SQLite + SQLCipher** (full-file encryption) | Battle-tested, zero-server, portable single file. |
| Key management | **Windows DPAPI** (`CryptProtectData`), key bound to the user account | No invented passwords; the Windows session unlocks the vault. Optional Windows Hello / TPM upgrade in a later phase. |
| Local model | **Ollama** running `qwen2.5:7b` (already installed in owner's stack) | Nightly distillation batch + future summarization; comfortable load for an RTX 5070 / 32 GB machine. |
| MCP server | **Python MCP SDK**, localhost only | First customers: the owner's own Claude installation and the KisiselAsistan system — self-dogfooding from day one. |
| Extension bridge (deferred) | Chrome **MV3 Native Messaging**; host manifest registered under `HKCU\Software\Google\Chrome\NativeMessagingHosts`, stdio transport | The Windows-concrete realization of Invariant 1. Architecture reserves the seam now; no code in MVP-0. |
| Audit log | **Append-only JSONL**, each line carrying the SHA-256 of the previous line (hash chain) | Dependency-free tamper evidence; the user can ask "what did you do yesterday?" and replay it. |
| Network anonymity (out of scope) | Optional SOCKS5/Tor proxy hook reserved for a later phase | Tor solves *network* anonymity; this project solves *data* sovereignty. Complementary, not competing — and Tor's exit-node/CAPTCHA friction is hostile to agentic flows. |

---

## 6. Memory Model and Permission Scopes

### 6.1 Three memory tiers

1. **Raw events** — append-only interaction records; **TTL 7–30 days**, then hard-deleted.
2. **Distilled profile** — the persistent layer. Produced nightly by the local model from raw events (§3.1). Constraints: human-readable JSON, user-editable, every fact carries provenance (which events produced it) and a timestamp.
3. **Portable export** — the entire profile as one encrypted file; restore on any machine. The vault is the single source; no cloud sync in MVP-0.

**The "Forget" guarantee:** `forget(topic)` performs genuine deletion (profile facts + any surviving raw events + a tombstone entry in the audit chain). Because the architecture keeps no raw shadow copies past TTL, deletion is provable — this is an engineering property, not a marketing claim.

### 6.2 Data scopes (OAuth-style)

`profile:read:<domain>` · `profile:read:all` · `profile:write` · `events:read` · `admin:forget` — granted per agent identity, revocable, every grant and every access audited.

### 6.3 Action classes (for later phases; defined now so the schema anticipates them)

| Class | Examples | Gate |
|---|---|---|
| A0 read | summarize page, read profile scope | free within granted scope |
| A1 write/fill | fill a form field | per-session confirmation |
| A2 submit/transact | send, purchase | explicit per-action confirmation + dry-run preview |
| A3 credentials/payment | passwords, card numbers | **never agent-mediated** — user types these personally, always |

---

## 7. Trust-Tiered Autonomy (T0–T3)

Autonomy is earned, never assumed (continuation of the owner's confidence-tiered-autonomy framework):

- **T0 — suggest only:** agent presents a plan; the user executes.
- **T1 — supervised execution:** step-by-step, every step visible and interruptible.
- **T2 — site-scoped autonomy:** flows the user has confirmed N times on a given site run automatically there.
- **T3 — full autonomy:** only explicitly allow-listed routines.

New installations start at T0. Tier promotion is a deliberate user decision, never a product default. A domain change mid-task forces an automatic pause (a task started on `amazon.de` cannot silently continue elsewhere).

---

## 8. MVP-0 Scope

**In scope (all local, no browser, no actions):**

1. Tray application: vault create / lock / unlock, status indicator.
2. Vault schema: `events` (TTL), `profile` (distilled, human-readable), `permissions`, `audit`.
3. Nightly distillation job (Ollama, §3.1) with QC: a distilled fact is committed only if the model can cite the supporting events (provenance check *before* raw events expire — verify against the source while the source still exists).
4. MCP server with tools: `profile_read(scope)`, `profile_write(fact)`, `forget(topic)`, `audit_read(range)` — every call scope-checked by the broker and appended to the audit chain.
5. `forget` with the genuine-deletion guarantee of §6.1.

**Explicitly out of scope for MVP-0:** browser extension, any web action (A1–A3), cloud masking/escalation, Tor integration, mobile, sync. *Rationale:* the action layer carries the overwhelming share of security and legal exposure; the vault alone is already independently valuable (memory portability across existing assistants) and independently testable.

**Roadmap after MVP-0 (indicative, owner-gated):** V0.2 read-only extension (page → event ingestion, T0 summaries) → V0.3 cloud escalation with masking (§3.2) → V0.4 action layer A1 at T1 → open-core packaging decision.

---

## 9. Threat Model (abbreviated)

| Threat | Mitigation |
|---|---|
| Prompt injection via page content | Invariant 3 (data/instruction separation); no goals from web text; A2 dry-run previews; domain-change pause |
| Malicious or over-curious agent client | Permission broker outside the model; deny-by-default scopes; per-agent identity; full audit chain |
| Local malware / vault theft | SQLCipher encryption; DPAPI-bound key; vault useless off-account (accepted residual risk: an attacker running *as the user* — standard for local-first designs) |
| Memory poisoning (false facts injected into profile) | Provenance requirement on every distilled fact; user-editable profile; QC-before-commit |
| Audit tampering | Hash-chained append-only log |

---

## 10. Governance Rules (BINDING for the implementing AI)

These rules were co-established with the owner in prior work and apply to **all** projects, including this one. The original formulation is Turkish; both are binding.

1. **Approved content is untouchable** (*Onaylanan içerik dokunulmaz*) — ask before changing anything already approved, even reformatting.
2. **Version numbers are proposed by the AI, declared by the owner.** This document proposes V0.1; the declaration is pending.
3. **Every change, even a single word, requires permission.**
4. **Plans are mandatory; optimization may be suggested but never imposed** — the owner decides.
5. **The T1–T5 checklist must be completed before implementation proceeds:**
   - **T1 (approval system):** proposed — each module is presented on completion; no progression without approval. *Pending owner confirmation.*
   - **T2 (version management):** V0.1 proposed (→ V0.2 on MVP-0 completion). *Pending owner declaration.*
   - **T3 (intervention threshold):** proposed — the AI may suggest optimizations; schema/scope changes only by owner decision. *Pending owner confirmation.*
   - **T4 (rules document):** proposed — place a `KURALLAR.md` containing these rules at the project root. *Pending owner confirmation.*
   - **T5 (project priority):** **open decision** — is this project a module of KisiselAsistan (the vault generalizes its memory layer) or an independent project? *Owner must decide before coding begins.*

Additional standing instruction from prior sessions: at the start of a new project or dialogue, proactively check for missing or forgotten context and help the owner fill the gaps. Known error log to avoid repeating: (1) approved content reformatted without permission, (2) version incremented without approval, (3) owner intent overridden by AI-side optimization, (4) approved content lost from context.

---

## 11. First Implementation Steps (upon T1–T5 completion)

1. Repository scaffold: `kasa/` with `src/vault/` (schema + SQLCipher wrapper), `src/mcp_server/`, `src/distill/`, `src/tray/`, `KURALLAR.md`, this brief as `docs/PROJECT_BRIEF.md`.
2. Vault schema DDL + DPAPI key wrapper + unit tests (create/lock/unlock/forget round-trip).
3. Audit hash-chain module + tamper test.
4. MCP server skeleton with `profile_read` stub, scope check, audit write.
5. Distillation prototype against synthetic events; QC provenance check.

Each step ends with a presentation to the owner per Rule/T1.

---

*Prepared by Claude (Anthropic) as a design handoff. All market probabilities in §2 are the designer's calibrated estimates, not guarantees. All pending decisions in §10 block implementation until resolved by the owner.*