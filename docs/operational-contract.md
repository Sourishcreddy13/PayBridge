# Operational Contract

## Initiation

Payment creation first validates the domain command, then atomically reserves the idempotency key together with the immutable payment row. This ordering prevents an orphan reservation.

## Processing

Processing appends `PROCESSING`, calls the persisted rail, records every adapter attempt, applies bounded transient retries, and appends the resulting terminal state.

## Reconciliation

Inbound settlement input is append-only. Reconciliation appends a separate result event so raw input remains unchanged. The latest result becomes the operational projection.

## Settlement

Settlement file generation is create-only. The path and SHA-256 checksum are recorded in the immutable settlement file table. Existing files cause a deterministic conflict.

## Refund

Refund creation does not mutate the original payment. It appends an immutable refund record and a `SETTLED -> REFUNDED` transition.

## Observability

Controller middleware creates a correlation ID; domain and application layers carry it as a request-scoped value. Error responses expose stable messages and the correlation ID but never SQL internals.
