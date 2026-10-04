from datetime import date
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database: str


class SettlementGenerationRequest(BaseModel):
    business_date: date
