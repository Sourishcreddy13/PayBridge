import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

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
)
from paybridge.application.payment_service import PaymentService
from paybridge.application.rail_service import RailService
from paybridge.application.reconciliation_service import ReconciliationService
from paybridge.application.refund_service import RefundService
from paybridge.application.retry import RetryPolicy
from paybridge.application.routing_service import RoutingService
from paybridge.application.settlement_import_service import SettlementImportService
from paybridge.application.settlement_service import SettlementService
from paybridge.application.timeline_service import TimelineService
from paybridge.controllers.dependencies import AuthContext, require_roles
from paybridge.controllers.schemas import HealthResponse, SettlementGenerationRequest
from paybridge.domain.enums import Rail, RailOutcome, Role
from paybridge.domain.exceptions import AuthenticationError, AuthorizationError, DomainError, ValidationError
from paybridge.domain.models import PaymentTransition, SettlementEntry
from paybridge.infrastructure.db import Database
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

configure_logging()
logger = logging.getLogger("paybridge.api")
settings = Settings()
database = Database(settings.database_path)
payment_repo = SQLitePaymentRepository(database)
routing_repo = SQLiteRoutingRepository(database)
audit_repo = SQLiteAuditRepository(database)
settlement_repo = SQLiteSettlementRepository(database)
refund_repo = SQLiteRefundRepository(database)
rail_attempt_repo = SQLiteRailAttemptRepository(database)

# Deterministic development scripts. The environment can be extended by replacing these adapters through composition.
adapters = {
    Rail.UPI.value: StubRailAdapter(Rail.UPI, RailScript((RailOutcome.SUCCESS,)), rail_attempt_repo),
    Rail.NEFT.value: StubRailAdapter(Rail.NEFT, RailScript((RailOutcome.SUCCESS,)), rail_attempt_repo),
    Rail.RTGS.value: StubRailAdapter(Rail.RTGS, RailScript((RailOutcome.SUCCESS,)), rail_attempt_repo),
    Rail.IMPS.value: StubRailAdapter(Rail.IMPS, RailScript((RailOutcome.SUCCESS,)), rail_attempt_repo),
}

# RailService uses an explicit resolver injected after routing persistence.
class AppRailService(RailService):
    def __init__(self) -> None:
        super().__init__(payment_repo, adapters)

    def _resolve_route(self, payment_id: UUID) -> str:
        route = routing_repo.get_route(payment_id)
        if route is None:
            raise ValidationError("Payment has no persisted routing decision")
        return route.value


rail_service = AppRailService()
audit_service = AuditService(audit_repo)
routing_service = RoutingService()
payment_service = PaymentService(
    payment_repo,
    routing_repo,
    routing_service,
    rail_service,
    audit_service,
    RetryPolicy(settings.retry_max_attempts, settings.retry_base_delay_seconds),
)
reconciliation_service = ReconciliationService(payment_repo, settlement_repo, audit_service)
settlement_service = SettlementService(payment_repo, routing_repo, settlement_repo, settings.settlement_dir)
refund_service = RefundService(payment_repo, refund_repo, audit_service)
dashboard_service = DashboardService(payment_repo, routing_repo, settlement_repo, refund_repo, SQLiteOpsReadModel(database))
timeline_service = TimelineService(payment_repo)
settlement_import_service = SettlementImportService(settlement_repo, audit_service)

CustomerAuth = Annotated[AuthContext, Depends(require_roles(Role.CUSTOMER))]
AnyPaymentAuth = Annotated[
    AuthContext, Depends(require_roles(Role.CUSTOMER, Role.OPS, Role.ADMIN))
]
OpsAuth = Annotated[AuthContext, Depends(require_roles(Role.OPS, Role.ADMIN))]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Schema is idempotent and local. Startup remains bounded because SQLite is local.
    database.connection().close()
    yield


app = FastAPI(title="PayBridge", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    request.state.correlation_id = correlation_id
    try:
        response = await call_next(request)
    except DomainError as exc:
        response = JSONResponse(status_code=400, content={"error": str(exc), "correlation_id": correlation_id})
    except Exception:
        logger.exception("unhandled request failure", extra={"correlation_id": correlation_id})
        response = JSONResponse(status_code=500, content={"error": "internal_error", "correlation_id": correlation_id})
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.exception_handler(AuthenticationError)
async def auth_error(_: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"error": str(exc)})


@app.exception_handler(AuthorizationError)
async def authorization_error(_: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"error": str(exc)})


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    connection = database.connection()
    connection.close()
    return HealthResponse(status="UP", database="UP")


@app.post("/api/v1/payments", response_model=PaymentView, status_code=201)
async def create_payment(
    command: CreatePaymentInput,
    request: Request,
    auth: CustomerAuth,
) -> PaymentView:
    return payment_service.create_payment(command, auth.actor, request.state.correlation_id)


@app.post("/api/v1/payments/{payment_id}/process", response_model=PaymentView)
async def process_payment(
    payment_id: UUID,
    request: Request,
    auth: AnyPaymentAuth,
) -> PaymentView:
    return payment_service.process_payment(payment_id, auth.actor, request.state.correlation_id)


@app.get("/api/v1/payments/{payment_id}", response_model=PaymentView)
async def get_payment(
    payment_id: UUID,
    auth: AnyPaymentAuth,
) -> PaymentView:
    return payment_service.get_payment(payment_id)


@app.get("/api/v1/payments", response_model=list[PaymentListItem])
async def payment_history(
    auth: AnyPaymentAuth,
) -> list[PaymentListItem]:
    return payment_service.history(auth.actor if auth.role is Role.CUSTOMER else "")


@app.post("/api/v1/payments/{payment_id}/refund", response_model=RefundView, status_code=201)
async def refund(
    payment_id: UUID,
    command: RefundInput,
    request: Request,
    auth: CustomerAuth,
) -> RefundView:
    return refund_service.request_refund(payment_id, command.amount, auth.actor, request.state.correlation_id)


@app.get("/api/v1/payments/{payment_id}/timeline")
async def payment_timeline(
    payment_id: UUID,
    auth: AnyPaymentAuth,
) -> list[PaymentTransition]:
    return timeline_service.get_timeline(payment_id)


@app.post("/api/v1/reconciliation/{business_date}")
async def reconcile(
    business_date: str,
    request: Request,
    auth: OpsAuth,
) -> list[SettlementEntry]:
    from datetime import date

    return reconciliation_service.reconcile(
        date.fromisoformat(business_date), auth.actor, request.state.correlation_id
    )


@app.post("/api/v1/settlement", response_model=dict)
async def generate_settlement(
    command: SettlementGenerationRequest,
    auth: OpsAuth,
) -> dict[str, str]:
    path = settlement_service.generate(command.business_date)
    return {"path": str(path), "business_date": command.business_date.isoformat()}


@app.get("/api/v1/ops/summary", response_model=OpsSummaryView)
async def ops_summary(
    auth: OpsAuth,
) -> OpsSummaryView:
    return dashboard_service.summary(datetime.now(tz=UTC).date())
