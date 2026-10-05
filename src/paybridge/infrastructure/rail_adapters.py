from dataclasses import dataclass

from paybridge.domain.enums import Rail, RailOutcome
from paybridge.domain.exceptions import ValidationError
from paybridge.domain.models import Payment, RailResponse

from .ports_runtime import RailOutcomeScriptStore


@dataclass(frozen=True, slots=True)
class RailScript:
    outcomes: tuple[RailOutcome, ...]
    reason_code: str = "SIMULATED"

    def __post_init__(self) -> None:
        if not self.outcomes:
            raise ValidationError("A rail script needs at least one outcome")
        if not all(isinstance(outcome, RailOutcome) for outcome in self.outcomes):
            raise ValidationError("Every rail script outcome must be a RailOutcome")


class StubRailAdapter:
    def __init__(self, rail: Rail, script: RailScript, store: RailOutcomeScriptStore) -> None:
        self.rail = rail
        self._script = script
        self._store = store

    def submit(self, payment: Payment, attempt: int) -> RailResponse:
        outcome_index = min(attempt - 1, len(self._script.outcomes) - 1)
        outcome = self._script.outcomes[outcome_index]
        external = f"{self.rail.value}-{str(payment.payment_id)[:8]}" if outcome is RailOutcome.SUCCESS else None
        self._store.record_attempt(payment.payment_id, self.rail, attempt, outcome, external, self._script.reason_code if outcome is not RailOutcome.SUCCESS else None)
        return RailResponse(outcome.value, external, None if outcome is RailOutcome.SUCCESS else self._script.reason_code, attempt)
