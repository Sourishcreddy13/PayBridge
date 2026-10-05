-- 001_initial: baseline schema. Migrations are append-only; never edit an applied file.
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    payment_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    account_masked TEXT NOT NULL,
    ifsc_masked TEXT NOT NULL,
    beneficiary_name_masked TEXT NOT NULL,
    beneficiary_type TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    narration TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    actor TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payment_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    reason_code TEXT,
    reason TEXT,
    FOREIGN KEY(payment_id) REFERENCES payments(payment_id)
);
CREATE TABLE IF NOT EXISTS routing_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id TEXT NOT NULL,
    rail TEXT NOT NULL,
    reason TEXT NOT NULL,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    FOREIGN KEY(payment_id) REFERENCES payments(payment_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    payment_id TEXT,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rail_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id TEXT NOT NULL,
    rail TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    external_reference TEXT,
    reason_code TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settlement_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_reference TEXT NOT NULL,
    payment_id TEXT,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    business_date TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reconciliation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_reference TEXT NOT NULL,
    payment_id TEXT,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    business_date TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settlement_files (
    business_date TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    checksum TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS refunds (
    refund_id TEXT PRIMARY KEY,
    original_payment_id TEXT NOT NULL,
    reverse_payment_id TEXT NOT NULL,
    amount TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    actor TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS prevent_payment_update BEFORE UPDATE ON payments BEGIN SELECT RAISE(ABORT, 'immutable payments'); END;
CREATE TRIGGER IF NOT EXISTS prevent_payment_delete BEFORE DELETE ON payments BEGIN SELECT RAISE(ABORT, 'immutable payments'); END;
CREATE TRIGGER IF NOT EXISTS prevent_transition_update BEFORE UPDATE ON payment_transitions BEGIN SELECT RAISE(ABORT, 'immutable transitions'); END;
CREATE TRIGGER IF NOT EXISTS prevent_transition_delete BEFORE DELETE ON payment_transitions BEGIN SELECT RAISE(ABORT, 'immutable transitions'); END;
CREATE TRIGGER IF NOT EXISTS prevent_settlement_update BEFORE UPDATE ON settlement_entries BEGIN SELECT RAISE(ABORT, 'immutable settlement entries'); END;
CREATE TRIGGER IF NOT EXISTS prevent_settlement_delete BEFORE DELETE ON settlement_entries BEGIN SELECT RAISE(ABORT, 'immutable settlement entries'); END;
CREATE TRIGGER IF NOT EXISTS prevent_refund_update BEFORE UPDATE ON refunds BEGIN SELECT RAISE(ABORT, 'immutable refunds'); END;
CREATE TRIGGER IF NOT EXISTS prevent_refund_delete BEFORE DELETE ON refunds BEGIN SELECT RAISE(ABORT, 'immutable refunds'); END;
CREATE TRIGGER IF NOT EXISTS prevent_reconciliation_update BEFORE UPDATE ON reconciliation_results BEGIN SELECT RAISE(ABORT, 'immutable reconciliation results'); END;
CREATE TRIGGER IF NOT EXISTS prevent_reconciliation_delete BEFORE DELETE ON reconciliation_results BEGIN SELECT RAISE(ABORT, 'immutable reconciliation results'); END;
