# Feature Specification: Standalone AoF GTO Solution Browser

**Feature Branch**: `001-aof-gto-browser`  
**Created**: 2026-03-12  
**Status**: Draft  
**Input**: User description: "Remove all-in or fold GTO solver integration from simulator and create standalone AoF GTO solution browser app with position/action selection and matrix metrics"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Browse Position-Specific Preflop Strategy (Priority: P1)

As a poker player studying all-in or fold strategy, I can open a dedicated AoF GTO browser, choose a table position, and immediately see the strategy matrix for that position.

**Why this priority**: Position-specific browsing is the core value of the new app and must work independently to make the feature usable.

**Independent Test**: Can be fully tested by opening the standalone app, selecting each position (UTG, BTN, SB, BB), and verifying the matrix updates per selection.

**Acceptance Scenarios**:

1. **Given** the standalone AoF GTO browser is open, **When** I select UTG, **Then** the matrix displays UTG strategy data.
2. **Given** the standalone AoF GTO browser is open, **When** I switch from UTG to BB, **Then** the matrix refreshes to BB strategy data without needing to restart the app.

---

### User Story 2 - Explore Action Outcomes by Position (Priority: P2)

As a poker player, I can toggle the action view (fold or all-in) for the selected position so I can compare recommended behavior by hand category.

**Why this priority**: Action-level browsing is required to turn strategy data into decision support.

**Independent Test**: Can be tested by selecting a fixed position, switching action mode between fold and all-in, and confirming matrix values change accordingly.

**Acceptance Scenarios**:

1. **Given** a position is selected, **When** I choose fold, **Then** the matrix displays fold-related values for that position.
2. **Given** a position is selected, **When** I choose all-in, **Then** the matrix displays all-in-related values for that position.

---

### User Story 3 - Compare Different Matrix Metrics (Priority: P3)

As a poker player, I can select which metric appears in the hand matrix (win/lose probability, EV, equity, or EQR) to analyze strategy from different perspectives.

**Why this priority**: Metric switching enhances analysis depth after core position/action browsing is available.

**Independent Test**: Can be tested by keeping the same position and action, changing metric from the dropdown, and confirming matrix labels/values update.

**Acceptance Scenarios**:

1. **Given** a position and action are selected, **When** I choose EV from the metric dropdown, **Then** the matrix displays EV values.
2. **Given** a position and action are selected, **When** I choose equity, **Then** the matrix displays equity values.

---

### Edge Cases

- If a selected position/action/metric context has no data, the UI MUST show a non-blocking empty-state message and render matrix cells with a missing-data state.
- During rapid switching between positions, actions, and metrics, the UI MUST apply only the latest selected context and MUST NOT display stale values.
- On first launch with no prior selections saved, the UI MUST load defaults (UTG, fold, win/lose probability) and render a valid matrix view.
- If one or more hand entries are invalid, only the affected cells MUST render invalid placeholders while valid cells remain visible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The all-in or fold GTO experience MUST be delivered as a standalone application within the HoPilot ecosystem and MUST NOT be embedded in the existing simulator GUI.
- **FR-002**: The existing simulator GUI MUST remain available and functionally unchanged for its current workflows after AoF integration is removed.
- **FR-003**: The standalone AoF application MUST present a hand matrix in the lower-middle area of the interface.
- **FR-004**: The standalone AoF application MUST display exactly four selectable player positions above the hand matrix: UTG, BTN, SB, and BB.
- **FR-005**: Users MUST be able to click/select any displayed position and view GTO results specific to that position.
- **FR-006**: For the selected position, users MUST be able to select action context for fold and all-in.
- **FR-007**: The interface MUST provide a dropdown control allowing the user to choose which metric to display in the matrix.
- **FR-008**: The metric dropdown MUST include win/lose probability, EV, equity, and EQR as selectable options.
- **FR-009**: When the selected position, action, or metric changes, the displayed matrix values MUST update to reflect the new selection context.
- **FR-010**: The matrix MUST display both suited and offsuit hand categories in a consistent, readable grid layout.
- **FR-011**: If no data is available for a selected context, the interface MUST show a clear non-blocking empty-state message instead of stale or misleading values.
- **FR-012**: The standalone AoF application MUST implement this information hierarchy: top control row with position selectors (UTG, BTN, SB, BB), visible action selector (fold/all-in), visible metric dropdown (win/lose probability, EV, equity, EQR), and a 13x13 hand matrix in the lower-middle region of the main view.
- **FR-013**: The standalone AoF application MUST highlight the active position, action, and metric simultaneously at all times.

### Assumptions

- Strategy data for the four required positions is available from existing AoF datasets or an equivalent approved source.
- The scope of this feature is browsing and visualization of solved AoF outcomes, not generating new solves within the interface.
- The standalone app will be launched from within the HoPilot ecosystem but will operate independently from simulator GUI screens.

### Key Entities *(include if feature involves data)*

- **Position Context**: One of UTG, BTN, SB, BB; controls which strategy slice is shown.
- **Action Context**: Decision mode for the selected position (fold or all-in).
- **Metric Type**: One of win/lose probability, EV, equity, or EQR; determines matrix value semantics.
- **Hand Matrix Cell**: A single hand category entry (pair, suited, or offsuit) with value and display state.
- **AoF View State**: Current user-selected combination of position, action, and metric used to drive what is shown.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pilot users can open the standalone AoF app and reach a valid matrix view for at least one position in under 30 seconds.
- **SC-002**: 95% of position switches (UTG/BTN/SB/BB) show updated matrix content within 1 second in normal operating conditions.
- **SC-003**: 95% of action switches (fold/all-in) and metric switches (win/lose probability, EV, equity, EQR) show updated matrix content within 1 second in normal operating conditions.
- **SC-004**: At least 90% of user acceptance test participants can correctly identify the selected position, action, and metric from the UI without assistance.
- **SC-005**: No regression is reported in simulator GUI workflows currently covered by existing regression tests after AoF integration removal.
