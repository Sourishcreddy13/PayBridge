from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from .enums import BeneficiaryType, PaymentState, Rail, ReconciliationStatus, RefundStatus
from .exceptions import ValidationError
from .money import parse_amount
from .currency_policy import validate_currency, validate_amount_band
from .beneficiary_policy import validate_beneficiary
from .payment_limits import validate_payment_limits
from .narration_policy import normalize_narration
from .audit_policy import validate_actor


@dataclass(frozen=True, slots=True)
class Beneficiary:
    account_number: str
    ifsc: str
    beneficiary_type: BeneficiaryType
    name: str

    def __post_init__(self) -> None:
        if not self.account_number.isdigit() or not 8 <= len(self.account_number) <= 18:
            raise ValidationError("Invalid beneficiary account")
        if len(self.ifsc.strip()) != 11:
            raise ValidationError("Invalid IFSC")
        if not self.name.strip():
            raise ValidationError("Beneficiary name is required")


@dataclass(frozen=True, slots=True)
class Payment:
    payment_id: UUID
    beneficiary: Beneficiary
    amount: Decimal
    narration: str
    idempotency_key: str
    currency: str
    created_at: datetime
    actor: str

    def __post_init__(self) -> None:
        normalized = parse_amount(self.amount)
        object.__setattr__(self, "amount", normalized)
        validate_currency(self.currency)
        validate_amount_band(normalized)
        validate_beneficiary(self.beneficiary)
        validate_payment_limits(normalized, self.beneficiary.beneficiary_type)
        object.__setattr__(self, "narration", normalize_narration(self.narration))
        validate_actor(self.actor)
        if not 8 <= len(self.idempotency_key) <= 128:
            raise ValidationError("Idempotency key length is invalid")
        if self.created_at.tzinfo is None:
            raise ValidationError("created_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class PaymentTransition:
    payment_id: UUID
    from_state: PaymentState
    to_state: PaymentState
    at: datetime
    actor: str
    reason_code: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    payment_id: UUID
    rail: Rail
    reason: str
    at: datetime
    actor: str


@dataclass(frozen=True, slots=True)
class RailResponse:
    outcome: str
    external_reference: str | None
    reason_code: str | None
    attempt: int


@dataclass(frozen=True, slots=True)
class SettlementEntry:
    external_reference: str
    payment_id: UUID | None
    amount: Decimal
    currency: str
    business_date: date
    status: ReconciliationStatus


@dataclass(frozen=True, slots=True)
class Refund:
    refund_id: UUID
    original_payment_id: UUID
    reverse_payment_id: UUID
    amount: Decimal
    status: RefundStatus
    requested_at: datetime
    actor: str


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)
