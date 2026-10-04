from typing import Protocol
from uuid import UUID

from paybridge.domain.enums import Rail, RailOutcome


class RailOutcomeScriptStore(Protocol):
    def record_attempt(self, payment_id: UUID, rail: Rail, attempt: int, outcome: RailOutcome, external_reference: str | None, reason_code: str | None) -> None: ...
