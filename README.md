# PayBridge — Payments Routing, Reconciliation & Settlement Hub

Business Case: **BC-AINE-009** · BFS — Payments Operations

PayBridge is a local-first, synthetic-data payments hub implementing payment initiation, idempotency, deterministic rail routing, stubbed rail execution with retry/backoff, reconciliation, immutable daily settlement files, refunds, audit history, and an operations dashboard.

## Architecture

The backend uses a layered architecture:

```text
HTTP Controller
    |
    v
Application Services
    |
    +---- Domain Rules / Immutable Models
    |
    +---- Repository Interfaces
              |
              v
       SQLite append-only store

Application Services -> Stub Rail Adapters
Application Services -> Structured Audit / Logging
React Frontend -> FastAPI Controller
```

Payment state is event-derived. The original payment row is never updated. A transition is appended to `payment_transitions`, and the latest valid transition becomes the current state. Every transition is validated against the *persisted* current state inside one write transaction (and again by a database trigger), so concurrent or repeated callers cannot double-submit a payment or double-refund it. A refund persists a real reverse-payment ledger record (`reverse_payments`) linked to the original payment and appends `REFUNDED`; only full refunds are supported.

The schema is owned solely by the numbered SQL files in `src/paybridge/infrastructure/migrations/`, applied once at startup and recorded in `schema_migrations`.

## Quick start

Requirements: Python 3.12+.

```bash
uv python install 3.12
uv sync --extra dev
cp .env.example .env
uv run python scripts/seed_data.py --settle-today
uv run uvicorn paybridge.main:app --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

### Authentication

Bearer tokens map to a unique *subject* (recorded as the actor in audit events) and a role. Configure them with `PAYBRIDGE_AUTH_TOKENS`, a JSON object `{"<token>": {"subject": "...", "role": "CUSTOMER|OPS|ADMIN"}}` (see `.env.example`).

- With `PAYBRIDGE_ENVIRONMENT=dev` (the default) and no tokens configured, three synthetic demo tokens exist (`customer-demo-token`, `ops-demo-token`, `admin-demo-token`) for local use and tests only.
- Any other environment refuses to start without explicit tokens of at least 24 characters that are not the demo values.
- Customers can only read and refund their own payments (other customers' payments return 404). Rail execution (`POST /payments/{id}/process`) is an OPS/ADMIN capability.

```bash
curl -H 'Authorization: Bearer customer-demo-token' http://127.0.0.1:8000/api/v1/me
```

### Refund policy

AC-08 specifies that a refund request immediately creates the reverse entry and moves the payment to `REFUNDED`; that is the default, audited under the requesting customer's identity. Set `PAYBRIDGE_REFUND_AUTO_APPROVE=false` to insert a `PENDING` state that operators approve or reject (`POST /api/v1/refunds/{id}/approve|reject`).

### Settlement import

Operators upload an inbound CSV (`external_reference,payment_id,amount,currency`) with `POST /api/v1/settlement/import?business_date=YYYY-MM-DD` (`Content-Type: text/csv`). The file checksum is its identity: re-importing identical bytes returns 409. Reconciliation matches by rail external reference first, then payment id, then a unique amount match, one-to-one; re-running it publishes only changed results.

## Requirements traceability

See `docs/requirements-matrix.md` for AC/NFR-to-code/test mapping.

## Run tests

```bash
uv run pytest -q --cov=src/paybridge --cov-report=term-missing --cov-report=xml:coverage.xml
uv run mypy
uv run ruff check src tests scripts
uv run lint-imports
bash .claude/hooks/amount-precision-check.sh   # also payment-immutability-check.sh, masked-pii-check.sh
```

Architecture checks are in `tests/architecture/`. AC-tagged tests use `pytest -m AC_01` through `AC_10`.

## Frontend

```bash
cd frontend
npm ci
npm run dev          # http://127.0.0.1:5173, proxies /api to :8000
npm run e2e          # Playwright: `mocked` (isolated + visual) and `integration` (real backend)
```

The React UI has no embedded credentials: people sign in with their access token. Customers get initiation, status/timeline tracking and refund request; operators get the dashboard (volumes by rail/status, processing, retry, unmatched and refund queues, settlement import/reconcile/generate). `tests/integration.spec.ts` runs against the real FastAPI app; `dashboard*.spec.ts` mock the API for isolated UI/error tests. The visual baseline lives in `frontend/tests/dashboard.visual.spec.ts-snapshots/`; regenerate it with `npx playwright test --project=mocked --update-snapshots` when the dashboard intentionally changes.

## AI-native substrate

The repository contains:

- Root and layered `CLAUDE.md` files plus `AGENTS.md` as a table of contents.
- Project-specific agents, skills, commands, and validation hooks under `.claude/`.
- Root `plugin.json` describing the PayBridge substrate.
- `.mcp.json` configuring Playwright MCP.
- `scripts/claude_agent_review.py` using the Claude Agent SDK programmatically.
- Sprint contracts and evaluator evidence under `sprint-contracts/` and `specs/reviews/`.
- Environment-first debugging evidence under `docs/`.

The repository is deliberately designed so production behavior is driven by specs and domain rules, while substrate files control agent work.

## Synthetic-data boundary

All seed data, tokens, account identifiers, names, and settlement records are synthetic. The application rejects obviously structured production-looking PII in log enrichment and never persists raw beneficiary account numbers or IFSC codes.

## CI/CD

`.gitlab-ci.yml` installs from the committed `uv.lock`, then runs ruff, strict mypy, import-linter, pytest with coverage, the three validation hooks, the frontend build/bundle-credential check/Playwright suites, and the Claude Agent SDK reviewer job (which validates the model's JSON against a schema and publishes `review-report.json`). The intended merge policy is PR/MR-only with protected `main`.

## Specification authority

The root requirements brief is transcribed into `specs/app_spec.md` and feature specifications. When implementation and specification differ, update the specification deliberately and regenerate the affected production code through the project agent workflow.
