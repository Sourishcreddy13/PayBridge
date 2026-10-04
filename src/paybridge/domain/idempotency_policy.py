import re

from .exceptions import ValidationError

_ALLOWED = re.compile(r"^[A-Za-z0-9._:-]+$")


def normalize_idempotency_key(value: str) -> str:
    key = value.strip()
    if not 8 <= len(key) <= 128:
        raise ValidationError("Idempotency key length is invalid")
    if not _ALLOWED.fullmatch(key):
        raise ValidationError("Idempotency key contains unsupported characters")
    return key
