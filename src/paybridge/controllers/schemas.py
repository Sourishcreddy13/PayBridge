from datetime import date

from pydantic import BaseModel, Field

from paybridge.domain.enums import Role


class HealthResponse(BaseModel):
    status: str
    database: str


class SettlementGenerationRequest(BaseModel):
    business_date: date


class RefundRejectionRequest(BaseModel):
    reason: str = Field(default="REJECTED", min_length=1, max_length=200)


class IdentityView(BaseModel):
    subject: str
    role: Role
