# Sprint 02 Contract — Rail Adapters + Retry

## Goal
Deliver AC-05 with deterministic stubbed adapters, retry/backoff, and terminal failure reason codes.

## Exit criteria
Transient faults retry within policy; terminal faults append `FAILED`; all attempts are observable.
