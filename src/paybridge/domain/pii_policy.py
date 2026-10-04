import re

_ACCOUNT_DIGITS = re.compile(r"^\d{8,18}$")


def mask_account_number(value: str) -> str:
    if _ACCOUNT_DIGITS.fullmatch(value):
        return "*" * max(0, len(value) - 4) + value[-4:]
    return "[masked]"


def mask_ifsc(value: str) -> str:
    cleaned = value.strip().upper()
    if len(cleaned) == 11:
        return f"{cleaned[:4]}*****{cleaned[-2:]}"
    return "[masked]"


def mask_name(value: str) -> str:
    tokens = [t for t in value.split() if t]
    return " ".join(token[0] + "***" for token in tokens) or "[masked]"
