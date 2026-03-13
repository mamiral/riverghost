# Phase 0 Research: Standalone AoF GTO Solution Browser

## Decision 1: AoF must be a separate GUI app from simulator
- Decision: Implement AoF browsing as a dedicated standalone GUI entrypoint/module, not a simulator panel.
- Rationale: The specification explicitly requires separation and simulator preservation. Existing coupling in simulator navigation and panel logic would continue to violate FR-001/FR-002.
- Alternatives considered:
  - Keep a simulator tab for AoF and hide by default: rejected because it is still embedded.
  - Keep shared window with mode switch: rejected because simulator remains structurally coupled to AoF UI.

## Decision 2: Reuse solver/domain modules, replace UI composition
- Decision: Retain existing AoF/GTO computation modules (`all_in_fold_gto.py`, `gto/gto_optimizer.py`, `gto/gto_models.py`) and build new AoF browser UI composition around them.
- Rationale: Preserves validated domain logic and lowers risk while enabling complete UI decoupling.
- Alternatives considered:
  - Rewrite solver and models for new app: rejected due to unnecessary risk and duplicated logic.
  - Keep current `GTOSolverPanel` unchanged: rejected because current panel supports broader modes and does not match required position/action/metric browsing flow.

## Decision 3: Represent browsing state as Position + Action + Metric context
- Decision: Use a single canonical view state (`position`, `action`, `metric`) to drive all matrix rendering.
- Rationale: Guarantees deterministic updates for FR-009 and simplifies event handling and tests.
- Alternatives considered:
  - Independent control state in each UI widget: rejected because it increases stale-state risk.
  - Implicit state inferred from selected matrix cell: rejected because controls must be explicit and user-driven.

## Decision 4: Use normalized 13x13 hand-matrix model for suited/offsuit/pairs
- Decision: Back matrix rendering with 169 canonical hand keys mapped to value payloads and display metadata.
- Rationale: Required by FR-010 and supports metric switching without recomputing layout.
- Alternatives considered:
  - Free-form list/table by hand rank: rejected because it does not mimic standard GTO matrix interaction.
  - Generate only populated cells from sparse data: rejected because users need stable visual matrix geography.

## Decision 5: Add explicit empty/error cell state handling
- Decision: For missing context data, render deterministic placeholders and top-level informational message instead of reusing previous values.
- Rationale: Directly satisfies FR-011 and prevents misleading analysis output.
- Alternatives considered:
  - Leave cells unchanged on missing data: rejected due to stale/misleading results.
  - Hard-fail and block UI interactions: rejected because browsing should remain non-blocking.

## Decision 6: Regression-first test strategy for simulator decoupling
- Decision: Update existing simulator and simulation-panel tests to assert removal of AoF controls and add new standalone AoF browser tests for selection/update behavior.
- Rationale: Constitution Principle VI requires comprehensive testing; this change introduces high regression risk in shared GUI modules.
- Alternatives considered:
  - Test only new app and skip simulator regression: rejected due to FR-002.
  - Rely on manual QA only: rejected as insufficient for repeatable protection.
