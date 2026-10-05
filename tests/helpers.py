"""Composable service stack for tests that need real SQLite repositories."""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from paybridge.application.audit import AuditService
from paybridge.application.dashboard_service import DashboardService
from paybridge.application.dto import BeneficiaryInput, CreatePaymentInput
from paybridge.application.payment_service import PaymentService
from paybridge.application.rail_service import RailService
from paybridge.application.reconciliation_service import ReconciliationService
from paybridge.application.refund_service import RefundService
from paybridge.application.retry import RetryPolicy
from paybridge.application.routing_service import RoutingService
from paybridge.application.settlement_import_service import SettlementImportService
from paybridge.application.settlement_service import SettlementService
from paybridge.domain.enums import BeneficiaryType, Rail, RailOutcome
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.rail_adapters import RailScript, StubRailAdapter
from paybridge.infrastructure.rail_attempt_repository import SQLiteRailAttemptRepository
from paybridge.infrastructure.read_models import SQLiteOpsReadModel
from paybridge.infrastructure.repositories import (
    SQLiteAuditRepository,
    SQLitePaymentRepository,
    SQLiteRefundRepository,
    SQLiteRoutingRepository,
    SQLiteSettlementRepository,
)


@dataclass
class Stack:
    db: Database
    payments: SQLitePaymentRepository
    routes: SQLiteRoutingRepository
    refunds_repo: SQLiteRefundRepository
    settlements_repo: SQLiteSettlementRepository
    attempts: SQLiteRailAttemptRepository
    payment_service: PaymentService
    refund_service: RefundService
    reconciliation: ReconciliationService
    settlement: SettlementService
    importer: SettlementImportService
    dashboard: DashboardService

    def rows(self, sql: str, *params: object) -> list[dict[str, object]]:
        conn = self.db.connection()
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()


def build_stack(tmp_path: Path, scripts: dict[Rail, tuple[RailOutcome, ...]] | None = None,
                adapters_override: dict[str, object] | None = None,
                auto_refund: bool = False) -> Stack:
    db = Database(tmp_path / "stack.db")
    payments = SQLitePaymentRepository(db)
    routes = SQLiteRoutingRepository(db)
    audit = AuditService(SQLiteAuditRepository(db))
    attempts = SQLiteRailAttemptRepository(db)
    refunds = SQLiteRefundRepository(db)
    settlements = SQLiteSettlementRepository(db)
    outcome_scripts = scripts or {}
    adapters = {
        rail.value: StubRailAdapter(
            rail, RailScript(outcome_scripts.get(rail, (RailOutcome.SUCCESS,))), attempts
        )
        for rail in Rail
    }
    if adapters_override:
        adapters.update(adapters_override)  # type: ignore[arg-type]
    rail_service = RailService(payments, adapters, routes)  # type: ignore[arg-type]
    return Stack(
        db, payments, routes, refunds, settlements, attempts,
        PaymentService(payments, routes, RoutingService(), rail_service, audit, RetryPolicy(3, Decimal(0))),
        RefundService(payments, refunds, auto_refund),
        ReconciliationService(payments, settlements, audit, attempts),
        SettlementService(payments, routes, settlements, tmp_path / "settlements"),
        SettlementImportService(settlements, audit),
        DashboardService(settlements, refunds, SQLiteOpsReadModel(db)),
    )


def command(key: str = "flow-idem-01", amount: str = "100.00", kind: BeneficiaryType = BeneficiaryType.RETAIL,
            urgent: bool = False) -> CreatePaymentInput:
    return CreatePaymentInput(
        beneficiary=BeneficiaryInput(
            name="Demo User", account_number="123456789012", ifsc="ABCD0123456", beneficiary_type=kind
        ),
        amount=Decimal(amount),
        narration="synthetic flow",
        idempotency_key=key,
        urgent=urgent,
    )
