from typing import Any

from fastapi import HTTPException

from paybridge.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DomainError,
    InvalidPaymentStateException,
    PaymentNotFound,
    RefundNotAllowed,
    SettlementAlreadyExists,
    SettlementImportAlreadyExists,
    ValidationError,
)


def map_domain_error(error: Exception) -> HTTPException:
    mapping: list[tuple[type[Exception], int]] = [
        (AuthenticationError, 401),
        (AuthorizationError, 403),
        (PaymentNotFound, 404),
        (InvalidPaymentStateException, 409),
        (RefundNotAllowed, 409),
        (SettlementAlreadyExists, 409),
        (SettlementImportAlreadyExists, 409),
        (ValidationError, 422),
    ]
    for error_type, status_code in mapping:
        if isinstance(error, error_type):
            return HTTPException(status_code=status_code, detail=str(error))
    if isinstance(error, DomainError):
        return HTTPException(status_code=400, detail=str(error))
    return HTTPException(status_code=500, detail="internal_error")


def safe_error_payload(error: Exception) -> dict[str, Any]:
    if isinstance(error, DomainError):
        return {"error": str(error)}
    return {"error": "internal_error"}
