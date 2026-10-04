#!/usr/bin/env python3
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paybridge.application.dto import BeneficiaryInput, CreatePaymentInput
from paybridge.main import payment_service, database, settings


def seed(settle_today: bool = False) -> None:
    commands = [
        CreatePaymentInput(
            beneficiary=BeneficiaryInput(name="Demo Retail User", account_number="123456789012", ifsc="ABCD0123456", beneficiary_type="RETAIL"),
            amount=Decimal("1250.00"), narration="Synthetic utility payment", idempotency_key="seed-retail-001",
        ),
        CreatePaymentInput(
            beneficiary=BeneficiaryInput(name="Demo Corporate User", account_number="987654321098", ifsc="WXYZ0987654", beneficiary_type="CORPORATE"),
            amount=Decimal("250000.00"), narration="Synthetic supplier payment", idempotency_key="seed-corporate-001",
        ),
    ]
    for command in commands:
        view = payment_service.create_payment(command, "seed-admin", "seed-correlation")
        if settle_today:
            payment_service.process_payment(view.payment_id, "seed-admin", "seed-correlation")
        print(view.model_dump(mode="json"))


if __name__ == "__main__":
    seed("--settle-today" in sys.argv)
