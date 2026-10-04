# Routing Rule Evaluator

## Purpose
Validate rail selection against amount, beneficiary type, currency, and configured eligibility.

## Required checks
- RTGS for amount >= 200000 INR.
- UPI for RETAIL amount <= 100000 INR.
- NEFT for remaining normal cases unless an explicit eligible IMPS override exists.
- Return a deterministic reason string.
- Never calculate money with float.
