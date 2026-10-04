from dataclasses import dataclass
from decimal import Decimal
from time import sleep
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: Decimal = Decimal("0")
    multiplier: Decimal = Decimal("2")

    def delay(self, retry_number: int) -> Decimal:
        return self.base_delay_seconds * (self.multiplier ** max(0, retry_number - 1))


def execute_with_retry(call: Callable[[int], T], is_retryable: Callable[[T], bool], policy: RetryPolicy) -> tuple[T, int]:
    attempt = 1
    while attempt <= policy.max_attempts:
        result = call(attempt)
        if not is_retryable(result) or attempt == policy.max_attempts:
            return result, attempt
        delay = policy.delay(attempt)
        if delay > Decimal("0"):
            sleep(delay)
        attempt += 1
    raise RuntimeError("Retry policy exhausted without a result")
