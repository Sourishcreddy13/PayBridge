import re

from .exceptions import ValidationError

_CONTROL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def normalize_narration(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValidationError("Narration is required")
    if _CONTROL.search(normalized):
        raise ValidationError("Narration contains unsupported control characters")
    return normalized[:250]

