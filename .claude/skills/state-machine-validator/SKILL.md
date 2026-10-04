# State Machine Validator

## Purpose
Verify payment lifecycle transitions.

## Allowed transitions
PENDING -> PROCESSING
PROCESSING -> SETTLED
PROCESSING -> FAILED
SETTLED -> REFUNDED

Any other transition raises InvalidPaymentStateException.
