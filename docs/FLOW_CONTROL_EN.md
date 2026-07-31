# KASA Flow-Control Layer (DEBI-0..3) — Cause → Decision → Effect

Date: 2026-07-31 · Status: implemented, 13 new tests, full suite 189 passed / 1 xfailed (pre-existing)

KASA's defensive architecture (encryption, authorization, injection barriers) was already
strong; its weak side was **resource governance**: nothing bounded how fast agents write,
how large the audit chain grows, or how many times the same event is stored. This layer
adds four deterministic valves. None of them relies on the model — consistent with the
project invariant "the model is not a security boundary" (KURALLAR §4).

---

## DEBI-0 — Per-agent rate limiting

- **Cause:** An agent stuck in a hallucination loop could call `event_ingest` /
  `profile_write` without limit. Every call writes to the vault *and* appends to the
  audit chain, so a single misbehaving agent could fill the disk and bloat the chain
  (local denial of service). No layer applied back-pressure.
- **Decision:** A token-bucket limiter (`src/mcp_server/ratelimit.py`, default burst 60,
  refill 1 token/s) enforced at the network boundary in `/v1/execute_tool` and
  `/v1/ingest`, **before** permission checks — because even a denied call does work
  (it writes an audit record). Buckets are per `agent_id`.
- **Effect:** Calls beyond capacity are rejected with HTTP 429 and touch neither the DB
  nor the audit chain. One runaway agent cannot starve others (isolated buckets), and
  total vault write throughput now has a hard ceiling.

## DEBI-1 — Event ingest deduplication (keyed hash + counter)

- **Cause:** Recurring events ("user opened mail", daily page views) were stored as new
  rows every time. Repetition inflated the disk, and — worse — inflated `forget()`,
  whose decrypt-scan cost is O(rows). The repetition count, the actually valuable
  *routine* signal, was never captured.
- **Decision:** At ingest, compute `content_hash = HMAC-SHA256(vault_key, source|type|content)`
  (after redaction, before encryption). On a match: no new row — increment
  `occurrence_count`, update `last_seen`, extend `ttl_expiry`, and reset `distilled=0`
  so the rising frequency re-enters distillation as fresh signal. A **keyed** hash was
  chosen deliberately: a plain SHA-256 of low-entropy content would allow dictionary
  attacks from the DB file alone; the HMAC key is DPAPI-protected, so the DB file by
  itself leaks no equality information.
- **Effect:** "Same event 365 times" becomes 1 row + a counter. Storage and
  `forget()` scan cost stop growing with repetition; the counter itself becomes the
  routine-detection input ("N repetitions = habit") that the user asked the system to
  understand — behavior, not raw logs.

## DEBI-2 — Audit chain checkpoint & archive

- **Cause:** The audit chain is append-only by design (T7: tamper-evident); rows could
  never be removed without breaking `verify_chain`. That guarantee had a cost: unbounded
  growth with no exit — a dead end.
- **Decision:** A new `audit_checkpoint` table seals the chain at its current tip
  (`upto_id`, `upto_hash`). `archive_up_to(checkpoint)` may delete **only sealed** rows.
  `verify_chain` seeds from the checkpoint hash instead of genesis — and the seed is
  *validated against the table*, not taken on faith: a first row whose `previous_hash`
  matches no recorded seal fails verification (tested). `_get_last_hash` falls back to
  the latest seal when the table is empty, so the chain stays continuous after a full
  archive. The tools (`audit_checkpoint` / `audit_archive`, scope `admin:audit`) are
  intentionally **not** in `PUBLIC_TOOLS`: archiving is an owner/maintenance act, never
  reachable from the network.
- **Effect:** Old audit ranges can be archived without breaking integrity; tampering
  after an archive is still detected. Unsealed records can never be deleted.
- **Side finding fixed:** `rotate_db_key` rebuilt the chain from a hardcoded genesis
  seed and left checkpoint seals pointing at stale hashes; the sequence
  *checkpoint → rotate → archive* would have broken verification. Rotation now preserves
  the first remaining row's seed and re-points live seals to their recomputed hashes.

## DEBI-3 — Provenance-preserving tombstones in prune

- **Cause:** `prune_expired_events` hard-deleted expired rows, but `profile.provenance`
  stores event IDs. Deleting a referenced row silently severed the "where did this
  profile fact come from" chain — the very auditability KASA builds elsewhere.
- **Decision:** During prune, rows referenced by any profile entry are not deleted;
  their `content` is replaced with a `tombstone:<content_hash>` marker (actual removal
  on disk — `secure_delete=ON`). Unreferenced rows are hard-deleted as before.
  Tombstones are excluded from dedup matching (a recurring event opens a fresh row) and
  from re-counting on later prunes (idempotent). `forget()` is deliberately **exempt**:
  the right to be forgotten (T5) outranks provenance, so it still hard-deletes.
- **Effect:** Sensitive content leaves the disk on schedule, while provenance remains
  resolvable. GDPR-style deletion is unchanged.

---

## Verification

`tests/test_flow_control.py` (13 tests): dedup single-row/counter, source-type
separation, distilled reset; 429 on overflow, per-agent bucket isolation; archive
preserves chain, tamper detected after archive, unsealed delete refused, spoofed seed
refused; tombstone vs delete split, prune idempotency, tombstone excluded from dedup,
`forget` still hard-deletes. Full suite: **189 passed, 1 xfailed** (pre-existing) — no
regressions.

## Compatibility

Schema changes are idempotent `ALTER TABLE` migrations applied on `Vault.connect()`;
existing vaults upgrade in place. `event_ingest` responses now include a
`deduplicated` field; `prune_expired_events` now returns `tombstoned` alongside
`deleted`.
