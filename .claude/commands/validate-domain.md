# Validate PayBridge Domain
Run:

```bash
pytest -q tests/domain tests/architecture
```

Then inspect Decimal usage, immutable dataclasses, and state transitions for AC-01..AC-04 and NFR-01..NFR-08.