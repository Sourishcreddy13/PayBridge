from .exceptions import ValidationError

MAX_ACTOR_LENGTH = 80
MAX_CORRELATION_LENGTH = 80


def validate_actor(actor: str) -> str:
    normalized = actor.strip()
    if not normalized or len(normalized) > MAX_ACTOR_LENGTH:
        raise ValidationError("Invalid actor")
    return normalized


def validate_correlation_id(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_CORRELATION_LENGTH:
        raise ValidationError("Invalid correlation ID")
    return normalized
