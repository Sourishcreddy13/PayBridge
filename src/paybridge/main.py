import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from paybridge.application.audit import AuditService
from paybridge.application.dashboard_service import DashboardService
from paybridge.application.dto import (
    CreatePaymentInput,
    OpsSummaryView,
    PaymentListItem,
    PaymentView,
    RefundInput,
    RefundView,
    SettlementImportView,
)
from paybridge.application.payment_service import PaymentService
from paybridge.application.rail_service import RailService
from paybridge.application.reconciliation_service import ReconciliationService
from paybridge.application.refund_service import RefundService
from paybridge.application.retry import RetryPolicy
from paybridge.application.routing_service import RoutingService
from paybridge.application.settlement_import_service import (
    MAX_IMPORT_BYTES,
    SettlementImportService,
)
from paybridge.application.settlement_service import SettlementService
from paybridge.application.timeline_service import TimelineService
from paybridge.controllers.dependencies import AuthContext, require_roles
from paybridge.controllers.response_mapper import map_domain_error
from paybridge.controllers.schemas import (
    HealthResponse,
    IdentityView,
    RefundRejectionRequest,
    SettlementGenerationRequest,
)
from paybridge.domain.audit_policy import normalize_correlation_id
from paybridge.domain.enums import Rail, RailOutcome, Role
from paybridge.domain.exceptions import DomainError, ValidationError
from paybridge.domain.models import PaymentTransition, SettlementEntry
from paybridge.infrastructure.db import Database
from paybridge.infrastructure.health_repository import SQLiteHealthRepository
from paybridge.infrastructure.logger import configure_logging
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
from paybridge.infrastructure.settings import Settings

logger = logging.getLogger("paybridge.api")

CustomerAuth = Annotated[AuthContext, Depends(require_roles(Role.CUSTOMER))]
AnyPaymentAuth = Annotated[AuthContext, Depends(require_roles(Role.CUSTOMER, Role.OPS, Role.ADMIN))]
OpsAuth = Annotated[AuthContext, Depends(require_roles(Role.OPS, Role.ADMIN))]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Composition root. Everything is built from ``settings`` so tests can use isolated state."""
    configure_logging()
    settings = settings or Settings()
    database = Database(settings.database_path)
    payment_repo = SQLitePaymentRepository(database)
    routing_repo = SQLiteRoutingRepository(database)
    audit_repo = SQLiteAuditRepository(database)
    settlement_repo = SQLiteSettlementRepository(database)
    refund_repo = SQLiteRefundRepository(database)
    rail_attempt_repo = SQLiteRailAttemptRepository(database)
    health_repo = SQLiteHealthRepository(database)

    # Deterministic development scripts. Replace these adapters through composition for real rails.
    adapters = {
        rail.value: StubRailAdapter(rail, RailScript((RailOutcome.SUCCESS,)), rail_attempt_repo)
        for rail in Rail
    }
    audit_service = AuditService(audit_repo)
    payment_service = PaymentService(
        payment_repo,
        routing_repo,
        RoutingService(),
        RailService(payment_repo, adapters, routing_repo),
        audit_service,
        RetryPolicy(settings.retry_max_attempts, settings.retry_base_delay_seconds),
    )
    reconciliation_service = ReconciliationService(
        payment_repo, settlement_repo, audit_service, rail_attempt_repo
    )
    settlement_service = SettlementService(payment_repo, routing_repo, settlement_repo, settings.settlement_dir)
    refund_service = RefundService(payment_repo, refund_repo, settings.refund_auto_approve)
    dashboard_service = DashboardService(settlement_repo, refund_repo, SQLiteOpsReadModel(database))
    timeline_service = TimelineService(payment_repo)
    settlement_import_service = SettlementImportService(settlement_repo, audit_service)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        health_repo.check()
        yield

    app = FastAPI(title="PayBridge", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.payment_service = payment_service  # for scripts such as seed_data.py

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = normalize_correlation_id(request.headers.get("X-Correlation-ID"))
        request.state.correlation_id = correlation_id
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled request failure", extra={"correlation_id": correlation_id})
            response = JSONResponse(
                status_code=500, content={"error": "internal_error", "correlation_id": correlation_id}
            )
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        mapped = map_domain_error(exc)
        correlation_id = getattr(request.state, "correlation_id", None)
        logger.info(
            "domain error", extra={"event": "domain_error", "correlation_id": correlation_id, "status": mapped.status_code}
        )
        return JSONResponse(
            status_code=mapped.status_code,
            content={"error": str(mapped.detail), "correlation_id": correlation_id},
        )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse | JSONResponse:
        try:
            health_repo.check()
        except RuntimeError:
            return JSONResponse(status_code=503, content={"status": "DOWN", "database": "DOWN"})
        return HealthResponse(status="UP", database="UP")

    @app.get("/api/v1/me", response_model=IdentityView)
    async def whoami(auth: AnyPaymentAuth) -> IdentityView:
        return IdentityView(subject=auth.actor, role=auth.role)

    @app.post("/api/v1/payments", response_model=PaymentView, status_code=201)
    async def create_payment(command: CreatePaymentInput, request: Request, auth: CustomerAuth) -> PaymentView:
        return payment_service.create_payment(command, auth.actor, request.state.correlation_id)

    @app.post("/api/v1/payments/{payment_id}/process", response_model=PaymentView)
    async def process_payment(payment_id: UUID, request: Request, auth: OpsAuth) -> PaymentView:
        # Rail execution is an operator capability, separate from customer initiation.
        return payment_service.process_payment(payment_id, auth.actor, request.state.correlation_id)

    @app.get("/api/v1/payments/{payment_id}", response_model=PaymentView)
    async def get_payment(payment_id: UUID, auth: AnyPaymentAuth) -> PaymentView:
        return payment_service.get_payment(payment_id, auth.owner_filter)

    @app.get("/api/v1/payments", response_model=list[PaymentListItem])
    async def payment_history(auth: AnyPaymentAuth) -> list[PaymentListItem]:
        return payment_service.history(auth.actor if auth.role is Role.CUSTOMER else "")

    @app.get("/api/v1/payments/{payment_id}/timeline")
    async def payment_timeline(payment_id: UUID, auth: AnyPaymentAuth) -> list[PaymentTransition]:
        payment_service.require_access(payment_id, auth.owner_filter)
        return timeline_service.get_timeline(payment_id)

    @app.post("/api/v1/payments/{payment_id}/refund", response_model=RefundView, status_code=201)
    async def request_refund(
        payment_id: UUID, command: RefundInput, request: Request, auth: CustomerAuth
    ) -> RefundView:
        return refund_service.request_refund(
            payment_id, command.amount, auth.actor, request.state.correlation_id, auth.owner_filter
        )

    @app.get("/api/v1/payments/{payment_id}/refund", response_model=RefundView)
    async def get_refund(payment_id: UUID, auth: AnyPaymentAuth) -> RefundView:
        return refund_service.get_for_payment(payment_id, auth.owner_filter)

    @app.post("/api/v1/refunds/{refund_id}/approve", response_model=RefundView)
    async def approve_refund(refund_id: UUID, request: Request, auth: OpsAuth) -> RefundView:
        return refund_service.approve_refund(refund_id, auth.actor, request.state.correlation_id)

    @app.post("/api/v1/refunds/{refund_id}/reject", response_model=RefundView)
    async def reject_refund(
        refund_id: UUID, command: RefundRejectionRequest, request: Request, auth: OpsAuth
    ) -> RefundView:
        return refund_service.reject_refund(refund_id, command.reason, auth.actor, request.state.correlation_id)

    @app.post("/api/v1/reconciliation/{business_date}")
    async def reconcile(business_date: date, request: Request, auth: OpsAuth) -> list[SettlementEntry]:
        return reconciliation_service.reconcile(business_date, auth.actor, request.state.correlation_id)

    @app.post("/api/v1/settlement/import", response_model=SettlementImportView, status_code=201)
    async def import_settlement(business_date: date, request: Request, auth: OpsAuth) -> SettlementImportView:
        content = await request.body()
        if len(content) > MAX_IMPORT_BYTES:
            raise ValidationError("Settlement input file is too large")
        entries, checksum = settlement_import_service.import_bytes(
            content, business_date, auth.actor, request.state.correlation_id
        )
        return SettlementImportView(business_date=business_date, entry_count=len(entries), checksum=checksum)

    @app.post("/api/v1/settlement", response_model=dict)
    async def generate_settlement(
        command: SettlementGenerationRequest, request: Request, auth: OpsAuth
    ) -> dict[str, str]:
        path = settlement_service.generate(command.business_date, request.state.correlation_id)
        return {"path": str(path), "business_date": command.business_date.isoformat()}

    @app.get("/api/v1/ops/summary", response_model=OpsSummaryView)
    async def ops_summary(auth: OpsAuth, business_date: date | None = None) -> OpsSummaryView:
        return dashboard_service.summary(business_date or datetime.now(tz=UTC).date())

    return app


app = create_app()
