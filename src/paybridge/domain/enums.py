from enum import StrEnum


class PaymentState(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class BeneficiaryType(StrEnum):
    RETAIL = "RETAIL"
    CORPORATE = "CORPORATE"


class Rail(StrEnum):
    UPI = "UPI"
    NEFT = "NEFT"
    RTGS = "RTGS"
    IMPS = "IMPS"


class RailOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"


class ReconciliationStatus(StrEnum):
    MATCHED = "MATCHED"
    UNMATCHED = "UNMATCHED"


class RefundStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Role(StrEnum):
    CUSTOMER = "CUSTOMER"
    OPS = "OPS"
    ADMIN = "ADMIN"
