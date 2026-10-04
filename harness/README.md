# Claude Harness Engine Integration

The capstone requires the Claude Harness Engine plugin as the base substrate. This repository declares it as the expected foundation and adds the PayBridge-specific layer in `.claude/`.

The evaluator-facing evidence is stored under `sprint-contracts/` and `specs/reviews/`. The project-specific agents are compatible with the Harness generator/evaluator/test-engineer roles and can be run within the same workflow.

Installation is intentionally left to the repository owner because the Harness plugin is an external substrate and is not part of this generated project payload.
