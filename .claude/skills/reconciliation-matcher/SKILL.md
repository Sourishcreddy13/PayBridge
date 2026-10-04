# Reconciliation Matcher

## Purpose
Match outbound payments to inbound settlement entries.

## Matching key
Prefer external reference, then normalized payment ID, then amount+currency+business date only when unique.

## Output
Every settlement line receives MATCHED or UNMATCHED status. Unmatched lines enter an exception queue.
