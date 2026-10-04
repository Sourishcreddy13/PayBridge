from csv import DictWriter
from datetime import date
from hashlib import sha256
from pathlib import Path

from paybridge.domain.exceptions import SettlementAlreadyExists
from paybridge.domain.settlement_policy import eligible_for_settlement, immutable_settlement_filename
from .ports import PaymentRepository, RoutingRepository, SettlementRepository


class SettlementService:
    def __init__(self, payments: PaymentRepository, routes: RoutingRepository, settlements: SettlementRepository, output_dir: Path) -> None:
        self._payments = payments
        self._routes = routes
        self._settlements = settlements
        self._output_dir = output_dir

    def generate(self, business_date: date) -> Path:
        if self._settlements.settlement_exists(business_date):
            raise SettlementAlreadyExists(f"Settlement already exists for {business_date.isoformat()}")
        eligible = [p for p in self._payments.list_settled(business_date) if eligible_for_settlement(
            self._payments.get_current_state(p.payment_id), business_date, p.created_at.date()
        )]
        self._output_dir.mkdir(parents=True, exist_ok=True)
        target = self._output_dir / immutable_settlement_filename(business_date)
        if target.exists():
            raise SettlementAlreadyExists(target.name)
        temp = target.with_suffix('.tmp')
        with temp.open('x', newline='', encoding='utf-8') as handle:
            writer = DictWriter(handle, fieldnames=['payment_id','amount','currency','rail','matched'])
            writer.writeheader()
            reconciliation = {r.payment_id: r.status.value for r in self._settlements.list_reconciliation_results(business_date) if r.payment_id}
            for payment in sorted(eligible, key=lambda p: str(p.payment_id)):
                writer.writerow({
                    'payment_id': str(payment.payment_id),
                    'amount': payment.amount,
                    'currency': payment.currency,
                    'rail': self._routes.get_route(payment.payment_id).value if self._routes.get_route(payment.payment_id) else '',
                    'matched': reconciliation.get(payment.payment_id, 'UNMATCHED'),
                })
        temp.replace(target)
        checksum = sha256(target.read_bytes()).hexdigest()
        self._settlements.append_file_record(business_date, str(target), checksum)
        return target
