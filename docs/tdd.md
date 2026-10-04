# TDD Discipline

PayBridge uses a red–green–refactor loop aligned to the acceptance criteria.

## Worked example: AC-02

**Red:** Add a test that creates a payment with idempotency key `idem-123`, repeats the request, expects the same `payment_id`, and asserts that the immutable payment count remains one.

**Green:** Implement idempotency reservation with a unique database constraint and replay lookup.

**Refactor:** Move the uniqueness rule into a dedicated domain policy and keep SQLite-specific conflict handling in the repository.

## Test organization

Each AC has a dedicated test module or a clearly marked test function. Domain tests remain framework-free. Integration tests use a temporary SQLite database. E2E tests exercise the browser surface. Architecture tests assert import direction and immutable table restrictions.
