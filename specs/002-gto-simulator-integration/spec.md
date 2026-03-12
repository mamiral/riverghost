# Feature Specification: GTO Analysis Integration in Poker Simulator

**Feature Branch**: `002-gto-simulator-integration`  
**Created**: 2026-03-03  
**Status**: Draft  
**Input**: User description: "GTO solver functionality needs to be incorporated into the poker simulator in GUI and not be a new panel!"

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

### User Story 1 - GTO Analysis in Poker Simulator (Priority: P1)

As a poker player using the simulator, I want to access GTO analysis directly within the poker simulator interface so that I can get optimal all-in strategy recommendations without switching between different panels, while retaining all existing simulator functionality for range assignment, card selection, and equity calculations.

**Why this priority**: This is the core requirement - enhancing the existing poker simulator with GTO analysis for all-in scenarios.

**Independent Test**: Can be fully tested by launching the poker simulator, setting up a hand scenario with ranges and cards (existing functionality), and verifying GTO analysis results appear within the same interface.

**Acceptance Scenarios**:

1. **Given** the poker simulator is running with a hand scenario configured (ranges assigned, cards selected), **When** the user clicks a "GTO Analysis" button in the simulator, **Then** GTO threshold and optimal all-in strategy information is displayed within the simulator interface alongside existing equity results
2. **Given** the simulator has bonus payout settings configured, **When** performing GTO analysis on an all-in scenario, **Then** the results correctly account for the bonus payouts in EV calculations
3. **Given** a hand is selected in the simulator with opponent ranges defined, **When** requesting GTO analysis for that specific all-in scenario, **Then** the system shows whether the hand should be played (ALL-IN) or folded based on GTO calculations, while preserving all existing simulator features

---

### User Story 2 - Integrated GTO Configuration (Priority: P2)

As a poker player, I want to configure GTO parameters (opponents, pot size, bet amount, bonuses) directly in the poker simulator interface so that I can easily adjust analysis settings for all-in scenarios without leaving the simulation context, while all existing simulator configuration options remain available.

**Why this priority**: Configuration needs to be seamless within the existing simulator workflow.

**Independent Test**: Can be fully tested by modifying GTO parameters in the simulator alongside existing range and card configurations, and verifying they affect GTO calculations for all-in scenarios.

**Acceptance Scenarios**:

1. **Given** the simulator is running with existing range and card configurations, **When** the user adjusts GTO parameters for an all-in scenario, **Then** GTO calculations use the updated parameters while preserving existing simulator settings
2. **Given** bonus payout settings are available in the simulator, **When** the user modifies bonus multipliers for tournament scenarios, **Then** subsequent GTO analyses for all-in situations incorporate the new bonus values

---

### Edge Cases

- What happens when GTO calculation is requested but no hand scenario is configured?
- How does the system handle very long GTO calculations (progress indication)?
- What if the user cancels a GTO calculation mid-process?
- How are GTO results cached to avoid redundant calculations for similar scenarios?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST preserve all existing poker simulator functionality (range assignment, card selection, equity calculations)
- **FR-002**: System MUST integrate GTO analysis functionality directly into the existing poker simulator GUI interface
- **FR-003**: System MUST provide a "GTO Analysis" button or menu option within the simulator for all-in scenarios
- **FR-004**: System MUST display GTO threshold results (equity requirement, optimal range) within the simulator interface for all-in decisions
- **FR-005**: System MUST allow configuration of GTO parameters (opponents, pot size, bet amount) in the simulator for all-in analysis
- **FR-006**: System MUST support bonus payout configuration within the simulator interface for tournament all-in scenarios
- **FR-007**: System MUST show GTO recommendations (ALL-IN/FOLD) for individual hands in all-in scenarios within the simulator
- **FR-008**: System MUST handle GTO calculation progress and cancellation within the simulator for long-running all-in analyses
- **FR-009**: System MUST cache GTO results to improve performance for repeated all-in scenario analyses

### Key Entities *(include if feature involves data)*

- **GTO Parameters**: Configuration for analysis including opponents, pot size, bet amount, bonus payouts
- **GTO Results**: Analysis output including threshold equity, optimal range, hand recommendations
- **Simulator State**: Current hand scenario and configuration in the poker simulator

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can access GTO analysis for all-in scenarios within the poker simulator interface without switching panels, while retaining all existing simulator functionality
- **SC-002**: GTO analysis completes and displays results in the simulator within 30 seconds for typical all-in scenarios
- **SC-003**: GTO parameter configuration is available directly in the simulator interface alongside existing configuration options
- **SC-004**: Bonus payout settings are configurable within the simulator and affect GTO calculations correctly for tournament all-in scenarios
- **SC-005**: Individual hand GTO recommendations (ALL-IN/FOLD) are displayed for selected hands in all-in scenarios within the simulator
