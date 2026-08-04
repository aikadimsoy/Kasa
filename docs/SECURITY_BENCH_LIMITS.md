# What the security benchmark does not cover

**Written 2026-08-04, after an adversarial audit of `tools/security_bench/` prompted by a
framing error found elsewhere in the project.**

Read this before quoting any number from
[`SECURITY_BENCHMARK.md`](SECURITY_BENCHMARK.md) or `security_bench_result.json`.

## Why this document exists

A probe in the *model* benchmark was found to be measuring the wrong adversary: it asked
the model, in the operator's own turn, to write malicious code — but KASA's threat model
**trusts the operator**, so a model obeying its owner cannot justify a permission broker
that does not defend against the owner either. The conclusion drawn from it was retracted.

The obvious follow-up question was whether that was one mistake or a *class* of mistake.
We audited the security benchmark the same way. It was a class of mistake. This document
records what that audit found, so the numbers are read with their limits attached.

## The benchmark was producing false passes, and we measured it

`tools/security_bench/run.py` did not set `KASA_ALLOWED_HOSTS`. That variable was set only
in `tests/conftest.py`, which does not execute when the bench runs via
`python -m tools.security_bench`. The bench drives the app with FastAPI's `TestClient`,
which sends `Host: testserver`; the G2 host guard (`src/mcp_server/server.py`) rejects any
non-loopback `Host` **before any authorization code runs**.

Measured on 2026-08-04, under bench conditions, three representative requests:

| Request | Result |
|---|---|
| no `Authorization` header | HTTP 400 — *"Geçersiz Host başlığı"* |
| wrong bearer token | HTTP 400 — *"Geçersiz Host başlığı"* |
| valid-shaped unauthorized call | HTTP 400 — *"Geçersiz Host başlığı"* |

`AUTHZ-DENY` — the only check cited as evidence for deny-by-default — has the predicate
`"PASS" if status != 200`. A 400 satisfies it. So the check reported PASS while
`VaultTools._check_permission` was never called. The permission broker was dormant and the
benchmark was green.

Fixed by setting the variable in `run.py`, with the reasoning recorded at the call site.
**The headline count did not change (18 PASS before, 18 PASS after the host fix), and that
coincidence is the point:** identical numbers, entirely different evidentiary value. Before
the fix they were produced by requests dying at the host guard; after it, by requests that
actually reach authorization code.

## Checks that cannot fail, or that pass through a gate other than the one they name

Confirmed by reading the check source against the server it claims to exercise:

| Check | Problem |
|---|---|
| `CRYPTO-DPAPI` | On Windows it appends PASS unconditionally. It never calls `protect_data`, never reads the key file, never confirms the key is DPAPI-wrapped. There is no failing branch on the target platform — yet DPAPI plus owner-only ACL is the *entire* stated defense against other OS accounts. |
| `AUTHZ-BIND` | Inspects the default argument of `start_server` via `inspect.signature`. The shipped desktop app never calls `start_server`; it binds in `src/desktop/launch.py`. Changing the real bind address to `0.0.0.0` would leave this check green. |
| `AUDIT-VERIFY` | Records entries and verifies them with the same hash function, on a chain built **without** the signing key production always supplies. A round-trip against itself. |
| `AUTHZ-C5` | Read as "the network cannot claim `system`". The 403 it records comes from the claimed-vs-bound identity mismatch, which returns 403 for *any* asserted id. The `RESERVED_AGENT_IDS` guard it is credited to is never reached. The dangerous case — a token actually bound to `system` — is untested. |
| `AUTHZ-DENY` | See above. Never reaches the permission broker. |

## Checks that model an adversary the threat model excludes

`docs/THREAT_MODEL.md` places malicious code running as the same OS user **out of scope**,
as accepted residual risk. All three `AUDIT-TAMPER-*` checks model exactly that adversary —
and model a *weaker* version of it: the bench builds the chain with `signing_key=None`,
while production passes an Ed25519 signing key (`src/vault/database.py`). In the tested
configuration the chain is a keyless forward hash link, so an attacker who can `UPDATE` the
table can also recompute the following hashes and pass verification. What the checks
demonstrate is detection of an attacker who edits a row *and forgets to rehash*. The
signature that would actually resist rewriting is never exercised.

## A deletion that is not detected

`AUDIT-TAMPER-DELETE` deletes a **middle** row and observes detection. `verify_chain` walks
forward and checks link continuity, so deleting the **tail** — `DELETE FROM audit WHERE id > N`
— leaves a chain that starts at genesis and links cleanly, and verification returns true.
Tail deletion is the deletion an attacker actually wants, because it erases the most recent
trail. It is neither tested nor detected. The material to close this already exists:
`audit_checkpoint` stores `entry_count` and `merkle_root`, but `verify_chain` uses the
checkpoint only to seed `last_hash`, never to detect a shortfall.

The check's report label is the unqualified "Audit Chain Deletion Detection", severity
critical. That label claims more than the code establishes.

## What is not covered at all

- **Injected page content / data-command confusion has no check in this benchmark.** That
  is the adversary KASA's architecture is built against, and the one that produced finding
  **F-POISON** (see [`SECURITY.md`](../SECURITY.md)): a distiller writing an attacker-chosen
  durable fact, 20 runs out of 20, with every authorization check passing. A benchmark that
  reports green while F-POISON is open is a benchmark whose scope is too narrow to speak to
  release readiness.
- **Owner-only ACL is never measured.** It is the stated primary defense against other OS
  accounts; no check asserts it.
- **Positive controls are almost entirely absent.** Only `CRYPTO-EXPORT`'s wrong-password
  pair qualifies. The project applies this discipline elsewhere — `tests/test_browser_optin_gate.py`
  carries both a negative control (the old vulnerable pattern is detected 3/3) and a positive
  one — but the security bench does not. Pairing every deny with a matching allow is the
  single change that would have caught every item above.
- **Two results are double-counted.** `FUZZ-NOAUTH` duplicates `AUTHZ-TOKEN-MISSING`;
  `CRYPTO-EXPORT` emits two results under one id. The "21 checks" figure is inflated.

## How to read the verdict word

The bench derives its verdict from the severity of failed checks. After the fixes above the
label reads **YAYIN-ADAYI** (release candidate). **Do not quote that as the project's
status.** It means "no check in this narrow suite currently fails" — not "the system is
ready". `README.md` and `SECURITY.md` remain the authority, and they say the project is not
release-ready, with the open findings enumerated.

A verdict computed from a suite that omits the project's own headline finding cannot be
evidence of readiness. That is the same error this document exists to record, one level up.

## Previously published numbers

`security_bench_result.json` was published carrying `commit: 2dfda9e`. **That object does not
exist in this repository** (`git cat-file -t 2dfda9e` → *not a valid object name*); the branch
was rewritten and the commit is unreachable, so the run is not reproducible from its own
stamp. Its recorded verdicts are also internally datable to a superseded server: it records
`AUTHZ-C7`/`C8` as HTTP 404, which is only possible before identity binding was added. Those
checks were pinned to `== 404` while their pytest twins in `tests/test_authz.py` had already
been updated to accept `(403, 404)`. They have now been aligned, and the check records
*which* rejection occurred rather than merely that one did.

---

**KASA** — a sovereign, local-first memory vault for agentic browsing.
Author: [@aikadimsoy](https://github.com/aikadimsoy) · Repository: <https://github.com/aikadimsoy/Kasa>
