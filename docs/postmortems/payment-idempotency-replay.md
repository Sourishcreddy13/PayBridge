# Post-mortem: Idempotency Replay

## Symptom

A repeated request could create two payment rows when the application checked for an existing idempotency key and then inserted the payment as separate operations.

## Environment-first diagnosis

The failure reproduced only under concurrent requests. Local tests used a single request path, so the race was invisible.

The repository layer was inspected first. The root cause was a non-atomic check-then-insert sequence.

## Resolution

Idempotency reservation is now a single SQLite transaction with a unique index on `idempotency_key`. A conflict loads the original reservation and returns its payment ID. Payment creation then appends exactly one immutable payment record.

## Preventive guardrails

- `tests/architecture/test_append_only.py` checks for update/delete statements in immutable repositories.
- `.claude/hooks/payment-immutability-check.sh` rejects prohibited mutation statements in source code.
- AC-02 integration tests include sequential and replay scenarios.
