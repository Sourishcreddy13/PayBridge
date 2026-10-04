from datetime import date

from .enums import PaymentState


def eligible_for_settlement(state: PaymentState, business_date: date, created_date: date) -> bool:
    return state is PaymentState.SETTLED and created_date == business_date


def immutable_settlement_filename(business_date: date) -> str:
    return f"settlement-{business_date.isoformat()}.csv"
