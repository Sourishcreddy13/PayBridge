-- 002_integrity: immutability of audit/routing/settlement evidence, refund workflow,
-- reverse-payment ledger, import idempotency and reconciliation projection support.

CREATE TRIGGER IF NOT EXISTS prevent_audit_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'immutable audit events'); END;
CREATE TRIGGER IF NOT EXISTS prevent_audit_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'immutable audit events'); END;
CREATE TRIGGER IF NOT EXISTS prevent_routing_update BEFORE UPDATE ON routing_decisions BEGIN SELECT RAISE(ABORT, 'immutable routing decisions'); END;
CREATE TRIGGER IF NOT EXISTS prevent_routing_delete BEFORE DELETE ON routing_decisions BEGIN SELECT RAISE(ABORT, 'immutable routing decisions'); END;
CREATE TRIGGER IF NOT EXISTS prevent_settlement_file_update BEFORE UPDATE ON settlement_files BEGIN SELECT RAISE(ABORT, 'immutable settlement files'); END;
CREATE TRIGGER IF NOT EXISTS prevent_settlement_file_delete BEFORE DELETE ON settlement_files BEGIN SELECT RAISE(ABORT, 'immutable settlement files'); END;

-- Payment transitions form a hash-free but strictly linear chain: the persisted from_state
-- must equal the previous to_state (PENDING for the first transition) and be a legal move.
CREATE TRIGGER IF NOT EXISTS enforce_transition_chain BEFORE INSERT ON payment_transitions
WHEN NEW.from_state IS NOT COALESCE(
        (SELECT to_state FROM payment_transitions WHERE payment_id = NEW.payment_id ORDER BY id DESC LIMIT 1),
        'PENDING')
  OR (NEW.from_state || '>' || NEW.to_state) NOT IN (
        'PENDING>PROCESSING', 'PENDING>FAILED', 'PROCESSING>SETTLED', 'PROCESSING>FAILED', 'SETTLED>REFUNDED')
BEGIN SELECT RAISE(ABORT, 'invalid payment transition'); END;

-- Reverse payments are real ledger records linked to the original payment.
CREATE TABLE IF NOT EXISTS reverse_payments (
    reverse_payment_id TEXT PRIMARY KEY,
    original_payment_id TEXT NOT NULL UNIQUE,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    FOREIGN KEY(original_payment_id) REFERENCES payments(payment_id)
);
CREATE TRIGGER IF NOT EXISTS prevent_reverse_payment_update BEFORE UPDATE ON reverse_payments BEGIN SELECT RAISE(ABORT, 'immutable reverse payments'); END;
CREATE TRIGGER IF NOT EXISTS prevent_reverse_payment_delete BEFORE DELETE ON reverse_payments BEGIN SELECT RAISE(ABORT, 'immutable reverse payments'); END;

-- Refunds are append-only. A refund request row never changes; its outcome is a separate,
-- immutable resolution row. Full refunds only, so at most one request per payment.
CREATE UNIQUE INDEX IF NOT EXISTS uq_refund_per_payment ON refunds(original_payment_id);
CREATE TABLE IF NOT EXISTS refund_resolutions (
    refund_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('COMPLETED', 'FAILED')),
    reason TEXT,
    resolved_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    FOREIGN KEY(refund_id) REFERENCES refunds(refund_id)
);
CREATE TRIGGER IF NOT EXISTS prevent_refund_resolution_update BEFORE UPDATE ON refund_resolutions BEGIN SELECT RAISE(ABORT, 'immutable refund resolutions'); END;
CREATE TRIGGER IF NOT EXISTS prevent_refund_resolution_delete BEFORE DELETE ON refund_resolutions BEGIN SELECT RAISE(ABORT, 'immutable refund resolutions'); END;

-- Settlement ingestion identity.
CREATE TABLE IF NOT EXISTS settlement_imports (
    checksum TEXT PRIMARY KEY,
    business_date TEXT NOT NULL,
    entry_count INTEGER NOT NULL,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS prevent_settlement_import_update BEFORE UPDATE ON settlement_imports BEGIN SELECT RAISE(ABORT, 'immutable settlement imports'); END;
CREATE TRIGGER IF NOT EXISTS prevent_settlement_import_delete BEFORE DELETE ON settlement_imports BEGIN SELECT RAISE(ABORT, 'immutable settlement imports'); END;
CREATE UNIQUE INDEX IF NOT EXISTS uq_settlement_entry_ref ON settlement_entries(business_date, external_reference);

CREATE INDEX IF NOT EXISTS ix_transitions_payment ON payment_transitions(payment_id, id);
CREATE INDEX IF NOT EXISTS ix_routing_payment ON routing_decisions(payment_id, id);
CREATE INDEX IF NOT EXISTS ix_recon_ref ON reconciliation_results(business_date, external_reference, id);
CREATE INDEX IF NOT EXISTS ix_rail_attempt_ref ON rail_attempts(external_reference);
