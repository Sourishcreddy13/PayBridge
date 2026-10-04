import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from paybridge.domain.enums import ReconciliationStatus
from paybridge.domain.exceptions import ValidationError
from paybridge.domain.models import SettlementEntry

from .audit import AuditService
from .ports import SettlementRepository


class SettlementImportService:
    def __init__(self, repository: SettlementRepository, audit: AuditService) -> None:
        self._repository = repository
        self._audit = audit

    def import_file(self, path: Path, business_date: date, actor: str, correlation_id: str) -> list[SettlementEntry]:
        if not path.exists() or not path.is_file():
            raise ValidationError("Settlement input file does not exist")
        entries: list[SettlementEntry] = []
        try:
            with path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                required = {"external_reference", "payment_id", "amount", "currency"}
                if not required <= set(reader.fieldnames or []):
                    raise ValidationError("Settlement file schema is invalid")
                for row in reader:
                    entries.append(self._parse_row(row, business_date))
        except (OSError, csv.Error) as exc:
            raise RuntimeError("Settlement input could not be read") from exc
        if not entries:
            raise ValidationError("Settlement input file is empty")
        self._repository.append_entries(entries)
        self._audit.record_event(
            "SETTLEMENT_IMPORTED", actor, correlation_id, None, {"entry_count": str(len(entries))}
        )
        return entries

    @staticmethod
    def _parse_row(row: dict[str, str], business_date: date) -> SettlementEntry:
        try:
            amount = Decimal(row["amount"])
            payment_id = UUID(row["payment_id"]) if row.get("payment_id") else None
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError("Settlement file contains invalid identifiers or amount") from exc
        if amount <= Decimal(0):
            raise ValidationError("Settlement amount must be positive")
        currency = row["currency"].strip().upper()
        if currency != "INR":
            raise ValidationError("Settlement currency must be INR")
        return SettlementEntry(
            row["external_reference"].strip(),
            payment_id,
            amount,
            currency,
            business_date,
            ReconciliationStatus.UNMATCHED,
        )
