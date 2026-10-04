# PR-Driven Git History Contract

The repository is intended to be developed with protected `main` and merge requests only. The local bootstrap history uses three no-fast-forward feature merges so the final repository retains the same structural evidence expected by the capstone.

Expected sequence:

1. `feature/domain-substrate` -> `main` (no-ff)
2. `feature/payment-processing` -> `main` (no-ff)
3. `feature/ops-workflows` -> `main` (no-ff)

No production changes are committed directly to `main` after bootstrap. GitLab protected-branch settings enforce the same rule remotely.
