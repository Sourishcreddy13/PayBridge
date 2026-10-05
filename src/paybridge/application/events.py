"""Structured lifecycle events. Every event carries correlation_id and, when known, payment_id."""

import logging
from uuid import UUID

_logger = logging.getLogger("paybridge.events")


def log_event(
    event: str,
    correlation_id: str,
    *,
    payment_id: UUID | None = None,
    actor: str | None = None,
    level: int = logging.INFO,
    **fields: str | int,
) -> None:
    extra: dict[str, object] = {"event": event, "correlation_id": correlation_id}
    if payment_id is not None:
        extra["payment_id"] = str(payment_id)
    if actor is not None:
        extra["actor"] = actor
    extra.update(fields)
    _logger.log(level, event, extra=extra)
