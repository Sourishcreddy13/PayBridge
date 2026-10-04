# Idempotency Guard

## Purpose
Protect payment creation from duplicate submissions and races.

## Required checks
- Idempotency key is normalized and length-bounded.
- Persistence uses a uniqueness constraint.
- A conflict returns the original payment ID.
- No second payment record is created.
