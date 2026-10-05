"""Canonical settlement-matching policy (mirrored by .claude/skills/reconciliation-matcher).

Order of preference for every inbound settlement line:
1. external reference known to the rail ledger,
2. normalized payment ID carried on the line,
3. amount + currency, only when exactly one candidate payment and one candidate line exist.

A payment can be matched by at most one settlement line per run; later duplicates are UNMATCHED.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import replace
from uuid import UUID

from .enums import ReconciliationStatus
from .models import Payment, SettlementEntry


def match_settlement(payment: Payment, entry: SettlementEntry) -> bool:
    """Value check: a candidate pairing must agree on currency and amount."""
    return entry.currency == payment.currency and entry.amount == payment.amount


def classify_entry(payment: Payment | None, entry: SettlementEntry) -> str:
    if payment is None or not match_settlement(payment, entry):
        return "UNMATCHED"
    if entry.payment_id is not None and entry.payment_id != payment.payment_id:
        return "UNMATCHED"
    return "MATCHED"


def reconcile_entries(
    entries: Sequence[SettlementEntry],
    payments: Mapping[UUID, Payment],
    references: Mapping[str, UUID],
) -> list[SettlementEntry]:
    """Return one result per input entry, in input order."""
    claimed: set[UUID] = set()
    resolved: dict[int, UUID] = {}

    def try_claim(index: int, entry: SettlementEntry, payment_id: UUID | None) -> None:
        if payment_id is None or payment_id in claimed:
            return
        payment = payments.get(payment_id)
        if payment is not None and match_settlement(payment, entry):
            claimed.add(payment_id)
            resolved[index] = payment_id

    for index, entry in enumerate(entries):
        try_claim(index, entry, references.get(entry.external_reference))
        if index not in resolved:
            try_claim(index, entry, entry.payment_id)

    remaining = [(i, e) for i, e in enumerate(entries) if i not in resolved and e.payment_id is None]
    line_counts = Counter((e.amount, e.currency) for _, e in remaining)
    open_payments: dict[tuple[object, str], list[UUID]] = {}
    for payment_id, payment in payments.items():
        if payment_id not in claimed:
            open_payments.setdefault((payment.amount, payment.currency), []).append(payment_id)
    for index, entry in remaining:
        key = (entry.amount, entry.currency)
        candidates = open_payments.get(key, [])
        if line_counts[key] == 1 and len(candidates) == 1:
            try_claim(index, entry, candidates[0])

    results: list[SettlementEntry] = []
    for index, entry in enumerate(entries):
        if index in resolved:
            results.append(
                replace(entry, payment_id=resolved[index], status=ReconciliationStatus.MATCHED)
            )
        else:
            results.append(replace(entry, status=ReconciliationStatus.UNMATCHED))
    return results
