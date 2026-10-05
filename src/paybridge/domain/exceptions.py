class DomainError(Exception):
    """Base class for deterministic domain failures."""


class ValidationError(DomainError):
    """Raised when domain input violates a business invariant."""


class InvalidPaymentStateException(DomainError):
    """Raised when a payment lifecycle transition is invalid."""

    def __init__(self, current: str, requested: str) -> None:
        super().__init__(f"Invalid payment transition: {current} -> {requested}")
        self.current = current
        self.requested = requested


class DuplicateIdempotencyKey(DomainError):
    """Raised internally when an idempotency reservation already exists."""


class PaymentNotFound(DomainError):
    """Raised when a payment cannot be found."""


class RefundNotAllowed(DomainError):
    """Raised when a refund is not permitted by the lifecycle policy."""


class SettlementAlreadyExists(DomainError):
    """Raised when an immutable settlement file already exists."""


class AuthenticationError(DomainError):
    """Raised when a credential is missing or invalid."""


class AuthorizationError(DomainError):
    """Raised when a role is insufficient for an operation."""


class SettlementImportAlreadyExists(DomainError):
    """Raised when an identical settlement file has already been imported."""
