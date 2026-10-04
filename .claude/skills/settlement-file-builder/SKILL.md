# Settlement File Builder

## Purpose
Create immutable daily settlement files.

## Required checks
- Include every SETTLED payment for the business date.
- Include reconciliation match indicator.
- Deterministically sort output.
- Reject overwrite of an existing settlement file.
