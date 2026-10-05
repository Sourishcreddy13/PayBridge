import os
import threading
from collections import defaultdict
from csv import DictWriter
from datetime import date
from hashlib import sha256
from pathlib import Path

from paybridge.domain.exceptions import SettlementAlreadyExists
from paybridge.domain.settlement_policy import immutable_settlement_filename

from .events import log_event
from .ports import PaymentRepository, RoutingRepository, SettlementRepository

_locks: defaultdict[str, threading.Lock] = defaultdict(threading.Lock)
_locks_guard = threading.Lock()


def _date_lock(key: str) -> threading.Lock:
    with _locks_guard:
        return _locks[key]


class SettlementService:
    """Generates the immutable daily settlement file.

    Protocol: render to a private temp file, publish it with an atomic exclusive hard link
    (never overwrites), then register it under the unique business_date key. If registration
    fails the file *this call* published is withdrawn. An orphan file left by a crash between
    publish and register is adopted when its checksum equals what would be generated now,
    otherwise it is reported as a conflict.
    """

    def __init__(
        self,
        payments: PaymentRepository,
        routes: RoutingRepository,
        settlements: SettlementRepository,
        output_dir: Path,
    ) -> None:
        self._payments = payments
        self._routes = routes
        self._settlements = settlements
        self._output_dir = output_dir

    def generate(self, business_date: date, correlation_id: str = "settlement") -> Path:
        with _date_lock(f"{self._output_dir}:{business_date.isoformat()}"):
            return self._generate_locked(business_date, correlation_id)

    def _generate_locked(self, business_date: date, correlation_id: str) -> Path:
        if self._settlements.settlement_exists(business_date):
            raise SettlementAlreadyExists(f"Settlement already exists for {business_date.isoformat()}")
        self._output_dir.mkdir(parents=True, exist_ok=True)
        target = self._output_dir / immutable_settlement_filename(business_date)
        temp = self._output_dir / f".{target.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            self._render(temp, business_date)
            checksum = sha256(temp.read_bytes()).hexdigest()
            try:
                os.link(temp, target)
            except FileExistsError as exc:
                if sha256(target.read_bytes()).hexdigest() != checksum:
                    raise SettlementAlreadyExists(target.name) from exc
                self._settlements.append_file_record(business_date, str(target), checksum)
                log_event("settlement_adopted", correlation_id, business_date=business_date.isoformat())
                return target
            try:
                self._settlements.append_file_record(business_date, str(target), checksum)
            except BaseException:
                target.unlink(missing_ok=True)
                raise
        finally:
            temp.unlink(missing_ok=True)
        log_event("settlement_generated", correlation_id, business_date=business_date.isoformat())
        return target

    def _render(self, temp: Path, business_date: date) -> None:
        eligible = self._payments.list_settled(business_date)
        reconciliation = {
            r.payment_id: r.status.value
            for r in self._settlements.list_reconciliation_results(business_date)
            if r.payment_id
        }
        with temp.open("w", newline="", encoding="utf-8") as handle:
            writer = DictWriter(handle, fieldnames=["payment_id", "amount", "currency", "rail", "matched"])
            writer.writeheader()
            for payment in sorted(eligible, key=lambda p: str(p.payment_id)):
                route = self._routes.get_route(payment.payment_id)
                writer.writerow(
                    {
                        "payment_id": str(payment.payment_id),
                        "amount": payment.amount,
                        "currency": payment.currency,
                        "rail": route.value if route is not None else "",
                        "matched": reconciliation.get(payment.payment_id, "UNMATCHED"),
                    }
                )
