# Requirements Traceability Matrix

| ID | Domain / Service | Test evidence | Runtime surface |
|---|---|---|---|
| AC-01 | `models.py`, `payment_service.py` | `tests/domain/test_models.py`, `tests/application/test_payment_service.py` | `POST /api/v1/payments` |
| AC-02 | `idempotency_policy.py`, repository reservation | repository/payment service tests | `POST /api/v1/payments` |
| AC-03 | `rail_policy.py` (single policy), `routing_service.py` | `tests/domain/test_routing.py` | payment creation |
| AC-04 | `state_machine.py` | `tests/domain/test_state_machine.py` | processing/refund |
| AC-05 | `retry.py`, `rail_adapters.py` | `tests/application/test_retry.py` | processing |
| AC-06 | `reconciliation_rules.py`, `reconciliation_service.py`, `settlement_import_service.py` | `tests/domain/test_reconciliation.py`, `tests/application/test_settlement_import_rules.py` | import + reconciliation endpoints |
| AC-07 | `settlement_policy.py`, `settlement_service.py` | `tests/application/test_settlement_service.py` | settlement endpoint |
| AC-08 | `refund_policy.py`, `refund_service.py`, `reverse_payments` table | `tests/application/test_refund_service.py`, `tests/integration/test_concurrency_and_atomicity.py` | refund endpoints |
| AC-09 | `audit.py`, audit repository | audit test | all state/routing paths |
| AC-10 | `dashboard_service.py`, `read_models.py` | controller RBAC test | ops summary endpoint |

NFR-01 is enforced by Decimal domain models and the precision hook. NFR-02/NFR-08 use database triggers and architecture tests. NFR-03 uses masking functions and the PII hook. NFR-04 uses controller dependencies. NFR-06 uses JSON logging. NFR-07 is the health route contract. NFR-05 is the migration runner (`infrastructure/db.py`) over `infrastructure/migrations/NNN_*.sql`, the only schema authority. NFR-06 emits lifecycle, rail-attempt, retry, reconciliation, settlement and refund events with `correlation_id`/`payment_id`/`actor` (`application/events.py`). NFR-08 is enforced atomically in the repository and by the `enforce_transition_chain` trigger.
