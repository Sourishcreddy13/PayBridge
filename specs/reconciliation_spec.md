# Reconciliation Specification

## Scope

This feature follows the PayBridge application specification and the business rules encoded under `src/paybridge/domain`.

## Acceptance Criteria

- **AC-06** — behavior is covered by an automated test bearing the same identifier.
- **AC-09** — behavior is covered by an automated test bearing the same identifier.

## Constraints

- No floating-point money arithmetic.
- Immutable business records.
- Stable error responses at controller boundaries.
- Synthetic data only.
