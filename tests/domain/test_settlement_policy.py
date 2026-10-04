from datetime import date
from paybridge.domain.enums import PaymentState
from paybridge.domain.settlement_policy import eligible_for_settlement, immutable_settlement_filename

def test_AC_07_settled_current_day_eligible(): assert eligible_for_settlement(PaymentState.SETTLED,date(2026,10,4),date(2026,10,4))
def test_AC_07_pending_not_eligible(): assert not eligible_for_settlement(PaymentState.PENDING,date(2026,10,4),date(2026,10,4))
def test_AC_07_filename(): assert immutable_settlement_filename(date(2026,10,4))=='settlement-2026-10-04.csv'
