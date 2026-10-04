from __future__ import annotations

from typing import TYPE_CHECKING

from .exceptions import ValidationError

if TYPE_CHECKING:
    from .models import Beneficiary

SUPPORTED_IFSC_PREFIXES = frozenset({"ABCD", "WXYZ", "BANK"})


def validate_beneficiary(beneficiary: Beneficiary) -> None:
    if beneficiary.ifsc[:4].upper() not in SUPPORTED_IFSC_PREFIXES:
        raise ValidationError("Beneficiary bank is not enabled in the synthetic environment")
    if beneficiary.name.strip().lower() in {"anonymous", "unknown"}:
        raise ValidationError("Beneficiary name is not acceptable")


def beneficiary_key(beneficiary: Beneficiary) -> str:
    return f"{beneficiary.ifsc.upper()}:{beneficiary.account_number[-4:]}:{beneficiary.beneficiary_type.value}"
