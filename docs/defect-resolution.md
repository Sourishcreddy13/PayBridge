# Defect Log Resolution

Status of every item in the "Defect & Vulnerability Log". Verified with: 249 pytest tests, ruff, strict mypy,
import-linter (2 contracts), the three hooks, `npm run build`, the bundle-credential check and 11 Playwright tests.

## Fixed in code

| Log item | Resolution |
|---|---|
| Precision hook rejects `sleep(float(delay))` (CRITICAL) | Hook allows only lines marked `# non-monetary: <why>`; it now uses `grep` (the old `rg` was absent from the CI image, so the gate could silently pass) and fails closed. Tested. |
| Concurrent `process_payment` double-submits (CRITICAL) | `append_transition` validates against the persisted state inside `BEGIN IMMEDIATE`; the loser raises before reaching the rail. Backed by an `enforce_transition_chain` trigger. Thread-race test. |
| Concurrent refunds (CRITICAL), idempotent refund | `complete_refund` is one transaction (transition + reverse payment + resolution + audit); unique index = one refund per payment. Thread-race tests. |
| Create not transactional (HIGH) | Idempotency key + payment + routing decision + audit commit together; rollback test. |
| Process/audit not coordinated (HIGH) | Transition and its audit event share one transaction; adapter exceptions end in `FAILED/RAIL_ERROR`, never stranded `PROCESSING`. |
| Object-level authorization; role-only identity; demo actor names (HIGH) | Tokens map to a unique subject + role; subject is the audit actor; customers get 404 for other customers' payments/timeline/refunds. |
| Customer can trigger processing (HIGH) | `process` is OPS/ADMIN only. |
| Customer refund with no approval (HIGH) | AC-08 specifies immediate completion, which stays the default (audited, owner-scoped, full-only). `PAYBRIDGE_REFUND_AUTO_APPROVE=false` adds PENDING + ops approve/reject. |
| Hard-coded credentials / ops token in bundle (HIGH) | Demo tokens only when `PAYBRIDGE_ENVIRONMENT=dev`; other environments require explicit unique tokens ≥24 chars. Frontend has a sign-in screen; CI checks the bundle for credentials. |
| Error mapper unused, 400 for everything (HIGH) | `response_mapper` is the single exception boundary (401/403/404/409/422). |
| Reconciliation date → 500 (HIGH) | Typed `date` path parameter (422). |
| Structured logs not emitted (HIGH) | `application/events.py`; lifecycle, rail attempt/retry, reconciliation, settlement, import and refund events carry `correlation_id`/`payment_id`/`actor`. |
| Correlation ID unvalidated (MED) | Validated (charset, ≤64) or replaced. |
| Audit / routing / settlement-file tables mutable (HIGH/MED) | Update/delete triggers on all three (and on new tables); tests in both directions. |
| `append_transition` bypasses state machine (HIGH) | Revalidated in the repository and by trigger. |
| Settlement check/create/register race; orphan file (HIGH) | Per-date lock, exclusive hard-link publish, unique registry key, withdrawal on failed registration, checksum-verified adoption of crash orphans. |
| Reconciliation duplicates / stale UNMATCHED (HIGH) | Unchanged results are not re-published; latest result per line is the projection. |
| Import not idempotent (HIGH) | Content-checksum import identity (409 on replay), atomic, unique (date, reference). |
| Matching policy vs skill; not one-to-one (HIGH/MED) | One canonical `reconcile_entries`: external reference → payment id → unique amount, one-to-one; skill file mirrors it. |
| Partial refund marks fully REFUNDED (HIGH) | Full refunds only; other amounts → 422. |
| No reverse payment record (HIGH) | `reverse_payments` ledger table with FK to the original payment. |
| Refund always COMPLETED (MED) | PENDING/COMPLETED/FAILED supported via immutable resolution rows. |
| `PaymentView.reason_code` missing (HIGH) | Projected from the latest transition. |
| Refunded payment dropped from settlement (HIGH) | Eligibility = existence of a SETTLED transition on the date. |
| Import amounts not quantized; reference unvalidated (MED) | `parse_amount` + reference checks. |
| RetryPolicy unvalidated (HIGH) | Validated at construction (fails closed). |
| Empty `RailScript` (MED) | Rejected at construction. |
| Two routing policies (HIGH) | One module, `rail_policy.py`; `validate_route` ≡ `select_rail`. |
| Dashboard N+1 / unused read model (MED) | Dashboard uses aggregate read-model queries only. |
| Unused abstractions (MED) | Deleted health/retry-pipeline/command-validator/queue services, settlement writer, refund-reference helper, dead injection/beneficiary-key functions; health route uses the health repository. |
| Two schema authorities (HIGH) | Numbered migrations are the only schema; applied once, recorded in `schema_migrations`; connections no longer create schema. |
| `Database.transaction()` broken (MED) | Real `@contextmanager`, used by repositories. |
| Reviewer script (HIGH ×3) | Evidence packet + rubric + example, JSON-schema `output_format`, strict parse/consistency validation, scoped test/lint tools, persisted `review-report.json`. |
| Prompt-injection control dead code (MED) | Removed (deterministic payment path). |
| `.mcp.json` `@latest` (MED) | Pinned to `@playwright/mcp@0.0.83`. |
| CI missing mypy / import-linter / lockfile (MED) | Added; CI installs from `uv.lock`. import-linter config was not being loaded at all (wrong section names) — fixed, now 2 kept contracts. |
| Frontend only ops view; ignores volumes/queues; "Today" wrong (HIGH/MED) | Customer portal (initiate/track/timeline/refund) and full ops dashboard; "Today" from backend business-date count. |
| Playwright mocks everything; no baseline (HIGH) | Real-backend integration project added; mocked tests kept for isolation; visual baseline committed. |
| No settlement import entry point (HIGH) | `POST /api/v1/settlement/import` + UI upload. |

## Not fixable by editing code (needs your environment)

- Claude Harness Engine installation and Generator→Evaluator→ratchet→PR traces.
- Git history: three no-fast-forward PR merges, zero direct commits to `main`.
- Authenticated output of `scripts/claude_agent_review.py` (the script is ready; it needs a Claude runtime).
- The "≈3,000 lines" expectation (source size was not padded; counting convention is yours to decide).
- The committed visual baseline was rendered with this workspace's Chromium; if CI's renders differently, run
  `npx playwright test --project=mocked --update-snapshots` once in CI and commit the result. The CI file was written
  but could not be executed here.
