# Contract: Provider Responsibilities Split

## Scope

Behavioral contracts for provider usage across precompute orchestration and browser payload retrieval paths.

## Contract A: Orchestration Context Contract

### Purpose

Provide validated scenario context for precompute orchestration and sweep dispatch.

### Inputs

- position
- metric
- position_actions
- optional pot_size and bet_amount overrides
- strict_current_action flag

### Required behavior

- Returns direct context fields required for execution contract construction.
- Performs context validation before orchestration proceeds.
- Emits invalid-context failures as orchestration boundary failures.

### Prohibited behavior

- Must not depend on browser payload retrieval methods.
- Must not require payload-specific formatting fields for orchestration.

## Contract B: Browser Payload Contract

### Purpose

Provide browser/UI-consumable matrix payload for read/query paths.

### Inputs

- position
- metric
- position_actions
- optional pot_size and bet_amount
- strict_current_action flag

### Required behavior

- Returns payload shape with context, matrix cells, status, and status_message.
- Supports AVAILABLE, MISSING, and NO_CONTEST outcomes without orchestration assumptions.
- Preserves existing payload semantics and backward-compatible fields.

### Prohibited behavior

- Must not require orchestration-run state to construct payload.
- Must not expose orchestration-only lifecycle internals.

## Contract C: Call-Site Enforcement

### Rule set

- Precompute runner/orchestration modules can only call Contract A.
- Browser panel/data retrieval modules can only call Contract B.
- Mixed usage in a single call path is a contract violation.

### Verification

- Unit/integration tests assert orchestration does not invoke payload retrieval.
- Browser payload tests assert read path remains functional independent of orchestration.

## Backward Compatibility Guarantees

- External precompute behavior remains unchanged.
- External browser payload behavior remains unchanged.
- Failure diagnostics keep existing semantic meaning.
