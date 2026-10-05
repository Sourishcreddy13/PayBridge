from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from paybridge.domain.enums import (
    BeneficiaryType,
    PaymentState,
    Rail,
    ReconciliationStatus,
    RefundStatus,
)
from paybridge.domain.idempotency_policy import normalize_idempotency_key
from paybridge.domain.money import parse_amount


class BeneficiaryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    account_number: str = Field(min_length=8, max_length=18)
    ifsc: str = Field(min_length=11, max_length=11)
    beneficiary_type: BeneficiaryType


class CreatePaymentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    beneficiary: BeneficiaryInput
    amount: Decimal
    narration: str = Field(min_length=1, max_length=250)
    idempotency_key: str = Field(min_length=8, max_length=128)
    urgent: bool = False

    @field_validator("amount")
    @classmethod
    def normalize_amount(cls, value: Decimal) -> Decimal:
        return parse_amount(value)

    @field_validator("idempotency_key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return normalize_idempotency_key(value)


class PaymentView(BaseModel):
    payment_id: UUID
    state: PaymentState
    amount: Decimal
    currency: str
    narration: str
    beneficiary_name: str
    masked_account_number: str
    masked_ifsc: str
    rail: Rail | None
    created_at: datetime
    reason_code: str | None = None


class PaymentListItem(BaseModel):
    payment_id: UUID
    state: PaymentState
    amount: Decimal
    currency: str
    rail: Rail | None
    created_at: datetime


class RefundInput(BaseModel):
    """Only full refunds are supported; ``amount`` may be omitted or equal the payment amount."""

    amount: Decimal | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal | None) -> Decimal | None:
        return parse_amount(value) if value is not None else None


class RefundView(BaseModel):
    refund_id: UUID
    original_payment_id: UUID
    reverse_payment_id: UUID
    amount: Decimal
    status: RefundStatus
    requested_at: datetime


class SettlementLineView(BaseModel):
    external_reference: str
    payment_id: UUID | None
    amount: Decimal
    currency: str
    status: ReconciliationStatus


class QueuedPaymentView(BaseModel):
    payment_id: UUID
    rail: Rail | None
    amount: Decimal
    created_at: datetime


class OpsSummaryView(BaseModel):
    business_date: date
    payments_today: int
    volumes_by_rail: dict[str, int]
    volumes_by_status: dict[str, int]
    unmatched_queue: list[SettlementLineView]
    refund_queue: list[RefundView]
    pending_queue: list[QueuedPaymentView]
    retry_queue: list[QueuedPaymentView]


class SettlementImportView(BaseModel):
    business_date: date
    entry_count: int
    checksum: str
