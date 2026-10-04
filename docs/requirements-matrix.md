# Requirements Traceability Matrix

| ID | Domain / Service | Test evidence | Runtime surface |
|---|---|---|---|
| AC-01 | `models.py`, `payment_service.py` | `tests/domain/test_models.py`, `tests/application/test_payment_service.py` | `POST /api/v1/payments` |
| AC-02 | `idempotency_policy.py`, repository reservation | repository/payment service tests | `POST /api/v1/payments` |
| AC-03 | `routing_rules.py`, `routing_service.py` | `tests/domain/test_routing.py` | payment creation |
| AC-04 | `state_machine.py` | `tests/domain/test_state_machine.py` | processing/refund |
| AC-05 | `retry.py`, `rail_adapters.py` | `tests/application/test_retry.py` | processing |
| AC-06 | `reconciliation_rules.py`, `reconciliation_service.py` | reconciliation tests | ops reconciliation endpoint |
| AC-07 | `settlement_policy.py`, `settlement_service.py` | settlement policy tests | settlement endpoint |
| AC-08 | `refund_policy.py`, `refund_service.py` | refund tests | refund endpoint |
| AC-09 | `audit.py`, audit repository | audit test | all state/routing paths |
| AC-10 | `dashboard_service.py`, `read_models.py` | controller RBAC test | ops summary endpoint |

NFR-01 is enforced by Decimal domain models and the precision hook. NFR-02/NFR-08 use database triggers and architecture tests. NFR-03 uses masking functions and the PII hook. NFR-04 uses controller dependencies. NFR-06 uses JSON logging. NFR-07 is the health route contract. NFR-05 is represented by `migrations/001_initial.sql` and the no-rewrite migration policy.
