# Operational Contract

## Initiation

Payment creation validates the command, selects the rail, then commits the idempotency key, immutable payment row, routing decision and their audit events in one transaction. A failure leaves nothing behind.

## Processing

Processing (ops/admin only) atomically reserves `PENDING -> PROCESSING` (a concurrent or repeated call fails before touching the rail), calls the persisted rail, records every adapter attempt, applies bounded transient retries, and appends the terminal state with its audit event in one transaction. An unexpected adapter error ends in `FAILED` with reason `RAIL_ERROR`, never a stranded `PROCESSING`. The retry policy is validated at construction.

## Reconciliation

Inbound settlement CSVs are imported once per content checksum (re-import => 409) and rejected atomically on any invalid row. Reconciliation matches by rail external reference, then payment id, then unique amount+currency, one settlement line per payment. Results are append-only; unchanged results are not re-published and the latest result per line is the operational projection.

## Settlement

Settlement generation is serialized per business date and create-only: render to a temp file, publish with an exclusive hard link, then register path + SHA-256 under the unique business date. A failed registration withdraws the file; an orphan from a crash is adopted only if its checksum matches. A payment settled on the date stays in that date's file even if refunded later.

## Refund

Refunds are full-amount only, at most one per payment, and owner-scoped for customers. Completion atomically appends the `SETTLED -> REFUNDED` transition, a `reverse_payments` ledger record linked to the original payment, an immutable resolution and audit events. By default completion is immediate (AC-08); `PAYBRIDGE_REFUND_AUTO_APPROVE=false` adds a PENDING state with ops approve/reject.

## Observability

Controller middleware creates a correlation ID; domain and application layers carry it as a request-scoped value. Error responses expose stable messages and the correlation ID but never SQL internals.
