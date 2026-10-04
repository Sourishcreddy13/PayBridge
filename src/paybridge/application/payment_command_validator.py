from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from paybridge.domain.beneficiary_policy import validate_beneficiary
from paybridge.domain.models import Beneficiary
from paybridge.domain.payment_limits import validate_payment_limits
from paybridge.domain.currency_policy import validate_currency, validate_amount_band
from paybridge.domain.narration_policy import normalize_narration, narration_is_prompt_injection_like
from paybridge.domain.idempotency_policy import normalize_idempotency_key


@dataclass(frozen=True, slots=True)
class NormalizedPaymentCommand:
    beneficiary: Beneficiary
    amount: Decimal
    narration: str
    idempotency_key: str
    urgent: bool


def validate_command(beneficiary: Beneficiary, amount: Decimal, narration: str, idempotency_key: str, urgent: bool = False) -> NormalizedPaymentCommand:
    validate_beneficiary(beneficiary)
    validate_currency("INR")
    validate_amount_band(amount)
    validate_payment_limits(amount, beneficiary.beneficiary_type)
    normalized_narration = normalize_narration(narration)
    if narration_is_prompt_injection_like(normalized_narration):
        normalized_narration = "[sanitized narration]"
    normalized_key = normalize_idempotency_key(idempotency_key)
    return NormalizedPaymentCommand(beneficiary, amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), normalized_narration, normalized_key, urgent)
