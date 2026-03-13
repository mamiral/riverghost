# Phase 0 Research: Solver-Backed AoF Browser Data

## Decision 1: Use adapter-based provider integration with existing solver modules
- Decision: Implement a solver adapter inside the AoF browser provider path that calls existing `AllInFoldGTOSolver` and `PokerAnalyzer` capabilities instead of direct UI-to-solver coupling.
- Rationale: Preserves modularity, keeps UI payload contract stable, and avoids reintroducing simulator coupling.
- Alternatives considered: Direct calls from GUI panel to solver methods, replacing provider with monolithic compute service.

## Decision 2: Preserve current payload contract exactly
- Decision: Keep `context + cells[169]` payload shape and status semantics so matrix rendering remains unchanged.
- Rationale: Reduces regression risk and isolates solver integration to provider internals.
- Alternatives considered: New payload schema with nested metric objects per cell.

## Decision 3: Deterministic edge-case policy is mandatory
- Decision: Define explicit behavior for all-fold, single-all-in, selected-fold, multiway all-in, invalid combo, timeout, and failure states.
- Rationale: Browser must avoid ambiguous or misleading strategy output and must remain testable.
- Alternatives considered: Best-effort dynamic behavior without formal policy.

## Decision 4: Context-keyed caching with explicit invalidation
- Decision: Cache payloads by selected position, full position-action map, metric, and calculation parameters.
- Rationale: Repeated toggles are common in browsing workflows; caching is needed to meet latency goals.
- Alternatives considered: No cache, or cache keyed only by selected position + metric.

## Decision 4b: Hybrid exact evaluation on cache miss
- Decision: On cache miss, evaluate sampled concrete combos through `AllInFoldGTOSolver.analyze_hand_strategy`; on cache hit, return payload immediately.
- Rationale: Provides solver-computed values while preserving interactive responsiveness on repeated contexts.
- Alternatives considered: Always-approximate model path, or always-exact full recomputation for every UI switch.

## Decision 5: Determinism controls for stochastic calculations
- Decision: Use fixed seeds and bounded simulation configuration in automated tests; allow configurable simulation depth for runtime.
- Rationale: Ensures repeatable CI assertions while preserving realistic runtime analysis behavior.
- Alternatives considered: Unseeded Monte Carlo in tests with tolerance-only assertions.

## Decision 6: Fallback policy is explicit degraded mode, not silent synthetic mode
- Decision: If solver computation fails or times out, return deterministic non-crashing payload with status messaging and logged degraded condition; no silent heuristic replacement in normal path.
- Rationale: Users must know when values are degraded; silent fallback undermines trust.
- Alternatives considered: Silent automatic fallback to current heuristic generation.

## Decision 7: Contract-first design for provider outputs
- Decision: Document a provider contract for context input, matrix payload output, edge-case statuses, and timeout/failure responses.
- Rationale: Aligns tests and implementation around one source of truth and prevents drift.
- Alternatives considered: Implicit behavior driven only by tests.
