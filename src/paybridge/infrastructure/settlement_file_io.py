from csv import DictWriter
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from paybridge.domain.models import SettlementEntry, Payment


class ImmutableSettlementFileWriter:
    def write(self, target: Path, rows: Iterable[dict[str, str]]) -> str:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(target)
        temporary = target.with_suffix(target.suffix + ".tmp")
        with temporary.open("x", newline="", encoding="utf-8") as handle:
            writer = DictWriter(handle, fieldnames=["payment_id", "amount", "currency", "rail", "matched"])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        temporary.replace(target)
        return sha256(target.read_bytes()).hexdigest()


def payment_row(payment: Payment, rail: str, matched: str) -> dict[str, str]:
    return {"payment_id": str(payment.payment_id), "amount": str(payment.amount), "currency": payment.currency, "rail": rail, "matched": matched}


def settlement_entry_row(entry: SettlementEntry) -> dict[str, str]:
    return {"payment_id": str(entry.payment_id) if entry.payment_id else "", "amount": str(entry.amount), "currency": entry.currency, "rail": "", "matched": entry.status.value}
