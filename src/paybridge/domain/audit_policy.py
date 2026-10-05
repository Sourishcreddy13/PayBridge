import re
from uuid import uuid4

from .exceptions import ValidationError

MAX_ACTOR_LENGTH = 80
MAX_CORRELATION_LENGTH = 64
_CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


def validate_actor(actor: str) -> str:
    normalized = actor.strip()
    if not normalized or len(normalized) > MAX_ACTOR_LENGTH:
        raise ValidationError("Invalid actor")
    return normalized


def validate_correlation_id(value: str) -> str:
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > MAX_CORRELATION_LENGTH
        or not _CORRELATION_PATTERN.fullmatch(normalized)
    ):
        raise ValidationError("Invalid correlation ID")
    return normalized


def normalize_correlation_id(value: str | None) -> str:
    """Accept a well-formed client correlation ID, otherwise generate a bounded replacement."""
    if value is not None:
        try:
            return validate_correlation_id(value)
        except ValidationError:
            pass
    return str(uuid4())
