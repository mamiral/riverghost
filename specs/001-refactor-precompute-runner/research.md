# Phase 0 Research: Precompute Orchestration Refactor

## Research Scope

Resolve implementation-shaping decisions before task generation:
- collaborator extraction scope
- provider context resolution policy
- repository split timing
- acceptance evidence strategy

## Decision 1: Collaborator extraction is in scope now

- **Decision**: Introduce collaborator classes/modules in this feature (not helper extraction only).
- **Reasoning**: The clarified scope explicitly requires modular decomposition now; delaying collaborators preserves existing coupling and weakens the refactor objective.
- **Alternatives considered**:
  - helper methods only: lower immediate diff but weaker boundaries
  - full architectural split across multiple subsystems: too broad for this feature

## Decision 2: Remove payload fallback in scenario context resolution

- **Decision**: `AoFPrecomputeRunner` orchestration uses direct context construction only; it does not fall back to payload retrieval.
- **Reasoning**: Clarification selected strict provider contract to reduce ambiguity and side effects from payload retrieval semantics.
- **Alternatives considered**:
  - `_build_context` first + payload fallback: more permissive but couples orchestration to display/payload flow
  - provider-type conditional fallback: adds policy complexity with limited value

## Decision 3: Defer full `DatabaseRepository` responsibility split

- **Decision**: Do not perform full repository separation in this feature.
- **Reasoning**: Keeps scope bounded to orchestration refactor while still preparing collaborator seams for a later split.
- **Alternatives considered**:
  - full split now: high risk and broad blast radius
  - no persistence collaborator extraction: misses key decomposition goals

## Decision 4: Acceptance evidence is automated tests

- **Decision**: Passing targeted automated tests is sufficient evidence.
- **Reasoning**: Fits clarified requirement and existing project QA workflow.
- **Alternatives considered**:
  - mandatory review signoff criterion: process-heavy and less objective
  - complexity metric thresholds: useful but not currently a required gate

## Key Risks and Mitigations

### Risk A: Behavioral drift in failure boundary mapping
- **Mitigation**: keep failure boundary names identical; add focused assertions in runner tests.

### Risk B: Regression in job/session state transitions
- **Mitigation**: preserve existing state-transition semantics; validate persisted counters and final state via integration tests.

### Risk C: Provider incompatibility after fallback removal
- **Mitigation**: enforce explicit orchestration failure classification when direct context cannot be resolved; document contract in `contracts/orchestration-contract.md`.

## Research Outcome

No unresolved clarifications remain. Planning can proceed to task generation with collaborator extraction, strict direct-context policy, and behavior-preserving test gates.
