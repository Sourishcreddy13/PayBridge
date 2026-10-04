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
    SETTLED --> REFUNDED: refund approved
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
    PaymentService->>Ledger: reserve idempotency key
    PaymentService->>Router: select rail
    Router-->>PaymentService: rail + reason
    PaymentService->>Ledger: append payment + audit
    Customer-->>API: payment_id / PENDING

    PaymentService->>Ledger: append PROCESSING
    PaymentService->>Rail: submit payment
    Rail-->>PaymentService: SUCCESS / TRANSIENT / PERMANENT
    alt transient
        PaymentService->>Rail: retry with backoff
    end
    PaymentService->>Ledger: append SETTLED or FAILED
```

## Immutability strategy

The `payments` table stores creation facts only. All state changes are appended to `payment_transitions`. Repositories expose append methods and read projections. Settlement files and audit events are also append-only. SQLite triggers reject changes to immutable records after insertion.

## Security boundaries

Authentication runs in controller dependencies. Customer endpoints accept the customer role. Operational queues and dashboard metrics require ops or admin. Sensitive data is masked before logging and persisted only in masked form where avoidable. Request correlation IDs are generated at the HTTP boundary and propagated through services.
