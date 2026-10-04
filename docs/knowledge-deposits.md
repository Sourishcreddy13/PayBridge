# Knowledge Deposits

| Recurring mistake | Deposit | Enforcement |
|---|---|---|
| Check-then-insert idempotency race | Reservation must be unique at persistence boundary | Unique index + repository transaction |
| Mutating settled payment | State is derived from append-only transitions | Architecture test + immutable table triggers |
| Logging account details | Sensitive identifiers are masked before log construction | PII policy + hook |
| Float arithmetic | Money uses Decimal only | `amount-precision-check.sh` + domain tests |
| Controller contains business rules | Controllers only validate/authenticate/map errors | Import architecture tests |

Domain substrate validation: routing, state, money, PII, and append-only policies are encoded as project-specific rules.
