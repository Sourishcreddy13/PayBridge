import csv
from datetime import date
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from paybridge.domain.enums import ReconciliationStatus
from paybridge.domain.exceptions import ValidationError
from paybridge.domain.models import SettlementEntry
from paybridge.domain.money import parse_amount

from .audit import AuditService
from .events import log_event
from .ports import SettlementRepository

MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_REFERENCE_LENGTH = 64
_REQUIRED_COLUMNS = {"external_reference", "payment_id", "amount", "currency"}


class SettlementImportService:
    def __init__(self, repository: SettlementRepository, audit: AuditService) -> None:
        self._repository = repository
        self._audit = audit

    def import_bytes(
        self, content: bytes, business_date: date, actor: str, correlation_id: str
    ) -> tuple[list[SettlementEntry], str]:
        """Validate and import a CSV. The content checksum is the import identity: importing the
        same bytes twice raises SettlementImportAlreadyExists and changes nothing."""
        if len(content) > MAX_IMPORT_BYTES:
            raise ValidationError("Settlement input file is too large")
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationError("Settlement input must be UTF-8 text") from exc
        checksum = sha256(content).hexdigest()
        try:
            reader = csv.DictReader(text.splitlines())
            if not _REQUIRED_COLUMNS <= set(reader.fieldnames or []):
                raise ValidationError("Settlement file schema is invalid")
            entries = [self._parse_row(row, business_date) for row in reader]
        except csv.Error as exc:
            raise ValidationError("Settlement input is not valid CSV") from exc
        if not entries:
            raise ValidationError("Settlement input file is empty")
        references = [e.external_reference for e in entries]
        if len(set(references)) != len(references):
            raise ValidationError("Settlement file repeats an external reference")
        self._repository.import_entries(entries, checksum, business_date, actor)
        self._audit.record_event(
            "SETTLEMENT_IMPORTED", actor, correlation_id, None,
            {"entry_count": str(len(entries)), "checksum": checksum, "business_date": business_date.isoformat()},
        )
        log_event(
            "settlement_imported", correlation_id, actor=actor,
            business_date=business_date.isoformat(), entries=len(entries),
        )
        return entries, checksum

    def import_file(
        self, path: Path, business_date: date, actor: str, correlation_id: str
    ) -> list[SettlementEntry]:
        if not path.exists() or not path.is_file():
            raise ValidationError("Settlement input file does not exist")
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise RuntimeError("Settlement input could not be read") from exc
        return self.import_bytes(content, business_date, actor, correlation_id)[0]

    @staticmethod
    def _parse_row(row: dict[str, str], business_date: date) -> SettlementEntry:
        reference = (row.get("external_reference") or "").strip()
        if not reference or len(reference) > MAX_REFERENCE_LENGTH or not reference.isprintable():
            raise ValidationError("Settlement external reference is missing or malformed")
        try:
            amount: Decimal = parse_amount((row.get("amount") or "").strip())
            raw_payment_id = (row.get("payment_id") or "").strip()
            payment_id = UUID(raw_payment_id) if raw_payment_id else None
        except ValueError as exc:
            raise ValidationError("Settlement file contains invalid identifiers or amount") from exc
        currency = (row.get("currency") or "").strip().upper()
        if currency != "INR":
            raise ValidationError("Settlement currency must be INR")
        return SettlementEntry(
            reference, payment_id, amount, currency, business_date, ReconciliationStatus.UNMATCHED
        )
