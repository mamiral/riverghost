# Feature Specification: Cell Detail Middle Panel

**Feature Branch**: `[001-cell-detail-panel]`  
**Created**: 2026-03-13  
**Status**: Ready for Implementation  
**Input**: User description: "Add a middle Cell Detail panel between the hand matrix and the right-side controls in the AoF browser GUI. When the user selects a cell, show metric-aware detail visuals including a vertical stacked bar for win/tie/loss in WIN_LOSE_PROBABILITY, with comparable detail views for EV, EQUITY, and EQR and status-aware fallbacks."

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

### User Story 1 - Inspect Selected Cell Details (Priority: P1)

As a user browsing the matrix, I can select any matrix cell and immediately see a dedicated detail view in a new middle panel so I can understand that cell without mentally decoding the grid.

**Why this priority**: Cell selection insight is the core value of the feature. Without it, the added panel does not serve a meaningful purpose.

**Independent Test**: Can be fully tested by opening the browser, selecting multiple cells, and confirming the middle panel always reflects the latest selected cell and shows an explicit empty-state when no cell is selected.

**Acceptance Scenarios**:

1. **Given** the matrix is visible and no cell is selected, **When** the screen renders, **Then** the middle panel shows a clear empty-state message.
2. **Given** the matrix is visible, **When** the user selects a cell, **Then** the middle panel updates to show details for that selected cell.
3. **Given** one cell is selected, **When** the user selects a different cell, **Then** the middle panel replaces the old details with the new selection details.

---

### User Story 2 - Metric-Aware Detail Visualization (Priority: P2)

As a user, I can switch metrics and see a metric-appropriate detail visualization for the selected cell so the panel remains useful across WIN_LOSE_PROBABILITY, EV, EQUITY, and EQR.

**Why this priority**: Metric awareness ensures the panel supports the full browsing workflow rather than only one metric mode.

**Independent Test**: Can be tested by selecting a single cell, switching metrics, and verifying the panel changes format and values appropriately, including status-aware fallback content.

**Acceptance Scenarios**:

1. **Given** a selected cell with available WIN_LOSE_PROBABILITY data, **When** the panel renders, **Then** it shows a vertical stacked bar with win, tie, and loss segments and readable values.
2. **Given** a selected cell and a non-WIN_LOSE_PROBABILITY metric, **When** the panel renders, **Then** it shows a metric title, a correctly formatted primary value, and a status row using the shared detail template.
3. **Given** a selected cell with non-available status (such as missing, timeout, error, or no contest), **When** the panel renders, **Then** it shows a clear status-aware fallback instead of blank or misleading values.

---

### User Story 3 - Preserve Compact Layout and Existing Controls (Priority: P3)

As a user, I can use the new middle detail panel without losing access, readability, or behavior in the existing matrix and right-side controls.

**Why this priority**: This prevents regressions in established workflows while introducing the new panel.

**Independent Test**: Can be tested by interacting with matrix selection, metric switching, and precompute controls before and after panel addition and verifying existing controls remain available and functional.

**Acceptance Scenarios**:

1. **Given** the new middle panel is present, **When** the browser renders, **Then** matrix and right-side controls remain visible and usable without overlap or clipping.
2. **Given** right-side precompute controls are used, **When** users interact with them, **Then** behavior remains unchanged relative to current expected behavior.

---

### Edge Cases

- No cell has been selected yet after initial render.
- User changes metric while the currently selected cell remains the same.
- User changes scenario context (position/action state) and selected cell detail must refresh to the new context values.
- Selected cell status is MISSING, TIMEOUT, ERROR, or NO_CONTEST.
- Selected cell includes partial or null metric values.
- Rapidly switching selected cells should not show stale values from the previous cell.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST render a new middle panel between the hand matrix and the right-side control stack.
- **FR-002**: System MUST update the middle panel whenever a matrix cell becomes selected.
- **FR-003**: System MUST show a clear empty-state message in the middle panel when no cell is selected.
- **FR-004**: System MUST update middle panel content when the selected metric changes.
- **FR-005**: System MUST render WIN_LOSE_PROBABILITY detail as a vertical stacked bar with win, tie, and loss segments.
- **FR-006**: System MUST display readable numeric values for each WIN_LOSE_PROBABILITY segment.
- **FR-007**: System MUST provide metric-specific detail views for EV, EQUITY, and EQR using a shared panel template with (a) a metric title row containing the active metric label, (b) a primary value row showing EV and EQR to 2 decimal places and EQUITY as a percentage to 1 decimal place, (c) a status row using the same fallback and status styling rules defined for FR-008, and (d) consistent spacing and typography tokens with the WIN_LOSE_PROBABILITY detail panel.
- **FR-008**: System MUST show status-aware fallback content in the middle panel for non-available cell statuses (including MISSING, TIMEOUT, ERROR, and NO_CONTEST when present).
- **FR-009**: System MUST refresh selected-cell detail values when scenario context changes (including position and action state changes).
- **FR-010**: System MUST preserve existing matrix interaction behavior and right-side control behavior after the middle panel is added.
- **FR-011**: System MUST keep the layout compact so all three areas (matrix, middle detail panel, right controls) remain visible and usable in the current browser window size.
- **FR-012**: System MUST include tests verifying selected-cell detail rendering, metric-switch updates, and fallback rendering for non-available statuses.

### Key Entities *(include if feature involves data)*

- **Cell Selection State**: Represents which matrix cell is currently selected; includes row/column identity and hand key.
- **Cell Detail View Model**: Represents metric-ready display values for a selected cell; includes selected metric, value components, status, and display labels.
- **Metric Segment**: Represents one display segment/value in the detail panel (for example win/tie/loss components or scalar metric value representation).

### Assumptions

- The matrix already exposes selection events or can be extended to do so without changing user-facing matrix behavior.
- Existing cell payloads already contain enough metric and status information to derive middle-panel content without new external data sources.
- The current browser window sizing baseline remains unchanged for this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In usability checks, selecting any visible matrix cell updates the middle panel within one interaction and always reflects the currently selected cell.
- **SC-002**: WIN_LOSE_PROBABILITY detail view shows all three components (win, tie, loss) with readable numeric values for 100% of AVAILABLE cells sampled in test coverage.
- **SC-003**: For each non-available status type covered by tests (MISSING, TIMEOUT, ERROR, and NO_CONTEST when present), the middle panel displays explicit fallback text in 100% of tested cases.
- **SC-004**: Regression tests confirm no behavior change in existing right-side precompute controls and core matrix interaction flows.
