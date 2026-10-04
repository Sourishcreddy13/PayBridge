from decimal import Decimal
from time import monotonic
from typing import Callable


class HealthService:
    def __init__(self, database_check: Callable[[], None]) -> None:
        self._database_check = database_check

    def check(self) -> tuple[str, Decimal]:
        started = monotonic()
        self._database_check()
        elapsed = Decimal(str(monotonic() - started))
        return "UP", elapsed
