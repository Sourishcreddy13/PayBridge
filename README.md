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

Payment state is event-derived. The original payment row is never updated. A transition is appended to `payment_transitions`, and the latest valid transition becomes the current state. Refunds create a new reverse entry and append `REFUNDED` to the original payment lifecycle.

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

Customer token example:

```bash
export PAYBRIDGE_CUSTOMER_TOKEN=customer-demo-token
curl -H 'Authorization: Bearer customer-demo-token' http://127.0.0.1:8000/api/v1/payments
```

The default development token values are synthetic and are intended only for the local capstone environment.

## Requirements traceability

See `docs/requirements-matrix.md` for AC/NFR-to-code/test mapping.

## Run tests

```bash
uv run pytest -q --cov=src/paybridge --cov-report=term-missing --cov-report=xml:coverage.xml
uv run mypy src
uv run ruff check src tests scripts
```

Architecture checks are in `tests/architecture/`. AC-tagged tests use `pytest -m AC_01` through `AC_10`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The React UI is responsive and consumes the FastAPI API. Playwright validation is under `frontend/tests/` and uses a committed snapshot baseline under `frontend/tests/snapshots/`.

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

`.gitlab-ci.yml` runs formatting, unit/integration tests, architecture tests, coverage generation, and the Claude Agent SDK reviewer job. The intended merge policy is PR/MR-only with protected `main`.

## Specification authority

The root requirements brief is transcribed into `specs/app_spec.md` and feature specifications. When implementation and specification differ, update the specification deliberately and regenerate the affected production code through the project agent workflow.
