# Autonomous Fix Loop — Idempotency Replay

1. Reviewer agent inspects AC-02 and runs the replay integration test.
2. The test exposes a duplicate insert path under a simulated conflict.
3. The agent identifies the repository check-then-insert sequence.
4. The agent changes the persistence boundary to unique reservation inside a transaction.
5. AC-02 and architecture tests are rerun.
6. Reviewer records the invariant: one idempotency key maps to one payment ID forever.
7. The resulting change is prepared for a merge request.
