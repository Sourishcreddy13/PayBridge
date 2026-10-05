# PayBridge Architecture

## Layered structure

```text
controllers  ->  application  ->  domain
     |              |             |
     +--------------+-------> ports
                              |
                         infrastructure
                              |
                        SQLite / stub rails
```

## Payment lifecycle

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> PROCESSING: process
    PROCESSING --> SETTLED: rail success
    PROCESSING --> FAILED: terminal failure
    SETTLED --> REFUNDED: refund completed (auto per AC-08, or operator-approved)
    PENDING --> FAILED: pre-processing rejection
    FAILED --> [*]
    REFUNDED --> [*]
```

## Routing and processing sequence

```mermaid
sequenceDiagram
    actor Customer
    participant API
    participant PaymentService
    participant Router
    participant Rail
    participant Ledger as AppendOnlyStore

    Customer->>API: POST /payments + idempotency key
    API->>PaymentService: validated command
    PaymentService->>Router: select rail
    Router-->>PaymentService: rail + reason
    PaymentService->>Ledger: ONE transaction: idempotency key + payment + routing + audit
    Customer-->>API: payment_id / PENDING

    PaymentService->>Ledger: atomic PENDING->PROCESSING (loser of a race fails here, before the rail)
    PaymentService->>Rail: submit payment
    Rail-->>PaymentService: SUCCESS / TRANSIENT / PERMANENT
    alt transient
        PaymentService->>Rail: retry with backoff
    end
    PaymentService->>Ledger: atomic SETTLED or FAILED + audit (adapter crash => FAILED/RAIL_ERROR)
```

## Immutability strategy

The `payments` table stores creation facts only. All state changes are appended to `payment_transitions`. Repositories expose append methods and read projections. Audit events, routing decisions, settlement entries/files/imports, refunds, refund resolutions, reverse payments and reconciliation results are also append-only; SQLite triggers reject UPDATE/DELETE on all of them. Reconciliation history is kept and the latest result per settlement line is the projection. A trigger additionally enforces a legal, gap-free transition chain.

## Security boundaries

Authentication runs in controller dependencies and yields a unique subject plus role; the subject is the audit actor. Customer endpoints accept the customer role and are object-scoped (a payment owned by someone else is a 404). Rail execution, refund approval, settlement import/reconciliation/generation, queues and dashboard metrics require ops or admin. Domain errors are mapped in one place (`response_mapper.py`): 401/403/404/409/422. Sensitive data is masked before logging and persisted only in masked form where avoidable. Request correlation IDs are generated at the HTTP boundary and propagated through services.
