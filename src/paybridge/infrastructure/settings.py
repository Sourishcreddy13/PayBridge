from decimal import Decimal
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PAYBRIDGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    database_path: Path = Path("runtime/paybridge.db")
    settlement_dir: Path = Path("runtime/settlements")
    customer_token: str = "customer-demo-token"
    ops_token: str = "ops-demo-token"
    admin_token: str = "admin-demo-token"
    retry_max_attempts: int = 3
    retry_base_delay_seconds: Decimal = Decimal(0)

    def token_roles(self) -> dict[str, str]:
        return {self.customer_token: "CUSTOMER", self.ops_token: "OPS", self.admin_token: "ADMIN"}
