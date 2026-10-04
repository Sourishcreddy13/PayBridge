# PayBridge Business Case

## Problem

A bank operates multiple payment rails but lacks one operational control plane for routing, retries, reconciliation, refunds, and settlement. PayBridge provides that hub with deterministic stubbed rails so the operating model is demonstrable without connecting to real payment networks.

## Target users

**Customers** initiate payments, inspect payment history, track lifecycle state, and request refunds.

**Operations users** inspect rail/status volumes, retry activity, unmatched settlement entries, and refund queues.

**Administrators** access operational summaries and governance endpoints.

## Success metrics

- Zero duplicate payment records for a repeated idempotency key.
- Correct deterministic rail selection for every routing rule case.
- No illegal lifecycle transitions.
- Every routing decision and state transition has an immutable audit record.
- Every settlement file is append-only and immutable.
- Unmatched reconciliation entries are visible to operations.

## Domain rules

- RTGS is selected for amounts at or above ₹2,00,000.
- UPI is selected for retail payments at or below ₹1,00,000.
- A default NEFT path handles the remaining normal cases.
- IMPS is available as a configured alternative route for eligible urgent cases, but no route can bypass the deterministic policy evaluator.
- Payment states are `PENDING`, `PROCESSING`, `SETTLED`, `FAILED`, and `REFUNDED`.
- Only `SETTLED` payments can enter `REFUNDED`.
- Transient rail failures are retried; terminal failures produce `FAILED` with a reason code.
- Refunds are separate reverse entries linked to the original payment.

## Value proposition

A single routing and operations boundary reduces payment-rail-specific logic in customer channels, makes failures observable, prevents duplicate submissions, and creates a reproducible settlement/reconciliation workflow suitable for controlled engineering exercises.
