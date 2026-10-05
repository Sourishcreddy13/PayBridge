# Evidence Status

## Locally validated

- Backend suite: 249 pytest tests pass (concurrency, atomicity, authorization, immutability, migrations, import/reconciliation/settlement idempotency, hooks, reviewer-script validation).
- `ruff check`, strict `mypy` and `lint-imports` (2 contracts) pass; the three validation hooks pass and are themselves tested, including that they fail closed.
- Frontend: `npm run build`, the credential-in-bundle check, 5 mocked Playwright tests and 6 integration tests against the real FastAPI backend pass in Chromium.
- A real visual baseline is committed at `frontend/tests/dashboard.visual.spec.ts-snapshots/dashboard-mocked-linux.png`.

## Must be produced in the learner's actual workspace

- Installation/execution trace of the external Claude Harness Engine plugin.
- Real Harness Generator -> Evaluator -> ratchet -> PR sprint outputs.
- Real GitLab merge-request history with at least three no-fast-forward merges and protected `main`.
- Output of `scripts/claude_agent_review.py` from an authenticated Claude Code runtime (`review-report.json`).
- A CI-generated visual baseline if the pipeline's Chromium renders differently from the committed one (`--update-snapshots`).

These records are intentionally not fabricated in the repository.
