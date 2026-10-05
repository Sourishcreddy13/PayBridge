import logging
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from time import sleep

from paybridge.domain.exceptions import ValidationError

logger = logging.getLogger("paybridge.retry")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: Decimal = Decimal(0)
    multiplier: Decimal = Decimal(2)

    def __post_init__(self) -> None:
        """Fail closed: an invalid policy never gets as far as processing a payment."""
        object.__setattr__(self, "base_delay_seconds", Decimal(str(self.base_delay_seconds)))
        object.__setattr__(self, "multiplier", Decimal(str(self.multiplier)))
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int):
            raise ValidationError("Retry max_attempts must be an integer")
        if not 1 <= self.max_attempts <= 10:
            raise ValidationError("Retry max_attempts must be between 1 and 10")
        if not self.base_delay_seconds.is_finite() or self.base_delay_seconds < 0:
            raise ValidationError("Retry base delay must be a finite value >= 0")
        if not self.multiplier.is_finite() or self.multiplier < 1:
            raise ValidationError("Retry multiplier must be a finite value >= 1")

    def delay(self, retry_number: int) -> Decimal:
        return self.base_delay_seconds * (self.multiplier ** max(0, retry_number - 1))


def execute_with_retry[T](
    call: Callable[[int], T],
    is_retryable: Callable[[T], bool],
    policy: RetryPolicy,
) -> tuple[T, int]:
    attempt = 1
    while True:
        result = call(attempt)
        if not is_retryable(result) or attempt >= policy.max_attempts:
            return result, attempt
        delay = policy.delay(attempt)
        logger.info("retrying after transient failure", extra={"event": "rail_retry", "attempt": attempt})
        if delay > Decimal(0):
            sleep(float(delay))  # non-monetary: wall-clock seconds
        attempt += 1
