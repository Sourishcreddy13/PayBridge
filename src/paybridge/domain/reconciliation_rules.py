from decimal import Decimal

from .models import Payment, SettlementEntry


def match_settlement(payment: Payment, entry: SettlementEntry) -> bool:
    if entry.currency != payment.currency:
        return False
    if entry.amount != payment.amount:
        return False
    if entry.payment_id is not None:
        return entry.payment_id == payment.payment_id
    return False


def classify_entry(payment: Payment | None, entry: SettlementEntry) -> str:
    if payment is not None and match_settlement(payment, entry):
        return "MATCHED"
    return "UNMATCHED"
