# Phase 0 Research: Cell Detail Middle Panel

## Decision 1: Add explicit selected-cell state in browser view state
- Decision: Introduce `selected_cell` (row, col, hand_key) as explicit UI state owned by AoF browser state/panel orchestration.
- Rationale: Selection must persist across redraws, react to metric changes, and be reset/retained predictably during scenario context refreshes.
- Alternatives considered:
  - Infer selection from transient mouse position: rejected because hover does not represent stable user intent.
  - Store selection in matrix component only: rejected because other components (detail panel) require shared state.

## Decision 2: Implement detail panel as standalone GUI component
- Decision: Create a new `aof_cell_detail_panel.py` component that receives a normalized view model and draws all metric-specific/fallback visual states.
- Rationale: Preserves modular design principle and prevents `AoFBrowserPanel` from becoming monolithic.
- Alternatives considered:
  - Draw detail visuals directly in `AoFBrowserPanel`: rejected due to coupling and reduced testability.
  - Extend matrix panel to draw detail area: rejected due to mixed responsibilities.

## Decision 3: Use status-first rendering guard
- Decision: Detail panel first checks cell status (`AVAILABLE`, `MISSING`, `TIMEOUT`, `ERROR`, `NO_CONTEST`) before metric rendering.
- Rationale: Prevents misleading visuals and guarantees explicit fallback behavior for non-available cells.
- Alternatives considered:
  - Render metric visuals with nulls and annotate later: rejected because it can imply valid values where none exist.

## Decision 4: WIN_LOSE_PROBABILITY visualization as vertical stacked segments
- Decision: For WIN_LOSE_PROBABILITY, render a single vertical stacked bar with win/tie/loss segment heights and labels.
- Rationale: Closely matches requested feature and provides immediate compositional understanding.
- Alternatives considered:
  - Horizontal stacked bar: rejected because request explicitly asks for vertical stacked layout.
  - Three separate bars: rejected because composition is harder to compare at a glance.

## Decision 5: Scalar metric rendering for EV/EQUITY/EQR with consistent visual language
- Decision: Render EV/EQUITY/EQR with a vertical scalar bar/value indicator using the same panel style and typography system.
- Rationale: Maintains visual continuity while respecting scalar nature of non-probability metrics.
- Alternatives considered:
  - Reuse win/tie/loss style with synthetic segments: rejected as semantically incorrect.
  - Text-only values: rejected due to weaker visual scanability.

## Decision 6: Compact 3-column layout using explicit width budgeting
- Decision: Recompute matrix width to allocate a fixed/controlled middle detail panel width while preserving right control panel width and margins.
- Rationale: Meets compact layout requirement and avoids right-side control regressions.
- Alternatives considered:
  - Overlay detail on matrix: rejected because it obscures grid usage.
  - Expand total window requirement: rejected to preserve existing window baseline.

## Decision 7: Extend GUI tests in existing suites
- Decision: Add selection/detail and fallback tests to existing AoF GUI test files instead of creating new test framework.
- Rationale: Aligns with current test organization and keeps regression checks near existing behavior tests.
- Alternatives considered:
  - Introduce separate visual snapshot harness: rejected as unnecessary for initial feature scope.
