# Phase 0 Research: Provider/Repository Responsibility Split

## Decision 1: Provider responsibilities split into two explicit contracts

- Decision: Define and enforce two provider contracts: orchestration context resolution and browser payload retrieval.
- Rationale: This directly enforces FR-001 through FR-003 and prevents accidental coupling between precompute orchestration and UI payload concerns.
- Alternatives considered: Keep a single provider interface with convention-only separation; this fails because call-site misuse remains possible and review-time detection is brittle.

## Decision 2: Orchestration is direct-context-only

- Decision: Precompute orchestration uses only direct context resolution methods and cannot use browser payload retrieval for scenario context.
- Rationale: This enforces FR-002 and preserves deterministic orchestration behavior independent of payload formatting logic.
- Alternatives considered: Fallback to payload retrieval when direct context fails; this fails because it reintroduces hidden coupling and changes failure classification behavior.

## Decision 3: Persistence split uses separate transactions with mandatory reconciliation/finalization

- Decision: Raw sweep persistence and job/session tracking persistence run in separate transactions, followed by a mandatory reconciliation/finalization pass.
- Rationale: This is the explicit clarification for this feature and is required by FR-011 through FR-013. It also keeps boundaries clear while guaranteeing deterministic post-run correctness.
- Alternatives considered: Single transaction across raw and tracking writes; rejected because it removes boundary isolation and increases lock/coupling risk between unrelated persistence concerns.

## Decision 4: Reconciliation behavior is deterministic and repeatable

- Decision: Reconciliation computes final scenario link/job outcomes from persisted raw and tracking records using deterministic rules and stable precedence.
- Rationale: Required by FR-013 and SC-006, and essential for reliability under split-write failures.
- Alternatives considered: Best-effort reconciliation with manual intervention; rejected because it violates mandatory correctness and repeatability requirements.

## Decision 5: No schema redesign in this feature

- Decision: Implement the split and reconciliation behavior without introducing schema changes.
- Rationale: The spec assumptions explicitly exclude schema redesign, and current entities already support required lifecycle and diagnostics.
- Alternatives considered: Add new reconciliation tables; rejected due to scope growth and incompatibility with the feature assumption.

## Decision 6: Verification strategy is targeted suites plus full regression

- Decision: Validate with targeted precompute/provider/repository suites and full tests run.
- Rationale: This aligns with success criteria SC-001 to SC-006 and constitution testing requirements.
- Alternatives considered: Targeted tests only; rejected because full-suite compatibility is part of backward behavior guarantees.

## Resolved Clarifications

All planning clarifications are resolved, including transaction consistency policy.

- Consistency model: separate transactions plus mandatory reconciliation/finalization pass.
- Provider boundary: strict split between orchestration context contract and browser payload contract.
- Reconciliation requirement: deterministic, mandatory, and repeatable for identical persisted inputs.
