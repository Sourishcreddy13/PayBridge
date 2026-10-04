# PayBridge Application Specification

## Source

Business Case `BC-AINE-009`, Payments Operations.

## Acceptance Criteria

### AC-01 — Initiate payment
Given a valid beneficiary, positive INR amount, narration, and idempotency key, when the customer initiates the payment, then the hub assigns a unique `payment_id`, persists the initial payment record and returns state `PENDING`.

### AC-02 — Idempotency replay
Given a previously accepted idempotency key, when the same key is submitted again, then the original `payment_id` is returned and no second payment record is created.

### AC-03 — Routing
Given amount and beneficiary type, when routing evaluates the payment, then it selects a supported rail and persists the reason.

### AC-04 — State machine
Given the payment lifecycle, when an invalid transition is requested, then `InvalidPaymentStateException` is raised and no invalid transition is persisted.

### AC-05 — Rail retry
Given a transient stubbed rail failure, when processing runs, then the configured retry policy is applied. A terminal failure results in `FAILED` with a reason code.

### AC-06 — Reconciliation
Given outbound payment records and settlement-file entries, when reconciliation runs, then matched entries are marked matched and unmatched entries appear in an exception report.

### AC-07 — Settlement
Given all settled payments for a business date, when settlement generation runs, then an immutable append-only file is written with matched/unmatched indicators.

### AC-08 — Refund
Given a settled payment, when a refund is requested, then a linked reverse entry is created and the original payment derives state `REFUNDED`.

### AC-09 — Audit
Given a state transition or routing decision, when persisted, then an immutable audit record contains timestamp, actor, correlation ID, and payment ID where applicable.

### AC-10 — Ops dashboard
Given ops/admin authentication, when the dashboard endpoints are queried, then volumes by rail/status and operational queues are returned.

## Non-Functional Requirements

- NFR-01 fixed-point monetary computation with `Decimal`.
- NFR-02 append-only business records.
- NFR-03 masked beneficiary/Payer data.
- NFR-04 controller-level RBAC.
- NFR-05 append-only migration history.
- NFR-06 structured JSON logs with correlation ID and payment ID.
- NFR-07 health response within one second after startup.
- NFR-08 architecture tests enforce idempotency uniqueness and settled-payment immutability.
