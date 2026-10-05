import json
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from paybridge.domain.audit_policy import validate_actor
from paybridge.domain.enums import Role

MIN_SECRET_LENGTH = 24

# Local-development identities. They exist only when PAYBRIDGE_ENVIRONMENT=dev (the default for
# tests) and are refused everywhere else.
DEV_TOKENS = {
    "customer-demo-token": ("demo-customer", Role.CUSTOMER),
    "ops-demo-token": ("demo-ops", Role.OPS),
    "admin-demo-token": ("demo-admin", Role.ADMIN),
}


class TokenIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(min_length=1, max_length=80)
    role: Role


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PAYBRIDGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    environment: Literal["dev", "staging", "production"] = "dev"
    database_path: Path = Path("runtime/paybridge.db")
    settlement_dir: Path = Path("runtime/settlements")
    # JSON object: {"<bearer token>": {"subject": "<unique principal id>", "role": "CUSTOMER|OPS|ADMIN"}}
    auth_tokens: str = ""
    # AC-08 specifies automatic completion. Set false to require operator approval of refunds.
    refund_auto_approve: bool = True
    retry_max_attempts: int = 3
    retry_base_delay_seconds: Decimal = Decimal(0)

    @model_validator(mode="after")
    def _require_explicit_secrets_outside_dev(self) -> "Settings":
        identities = self.token_identities()
        if self.environment != "dev":
            if not self.auth_tokens.strip():
                raise ValueError("PAYBRIDGE_AUTH_TOKENS must be set outside the dev environment")
            for token in identities:
                if len(token) < MIN_SECRET_LENGTH or token in DEV_TOKENS:
                    raise ValueError("Bearer tokens must be unique, non-default and long enough")
        return self

    def token_identities(self) -> dict[str, tuple[str, Role]]:
        """Bearer token -> (unique subject identifier, role)."""
        if not self.auth_tokens.strip():
            return dict(DEV_TOKENS) if self.environment == "dev" else {}
        try:
            raw = json.loads(self.auth_tokens)
            parsed = {token: TokenIdentity.model_validate(value) for token, value in raw.items()}
        except (ValueError, AttributeError) as exc:
            raise ValueError("PAYBRIDGE_AUTH_TOKENS must be a JSON object of token identities") from exc
        return {token: (validate_actor(i.subject), i.role) for token, i in parsed.items()}
