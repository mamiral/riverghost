# Feature Specification: Integrate State Machine into AOF GTO Browser GUI

**Feature Branch**: `001-state-machine-integration`  
**Created**: March 18, 2026  
**Status**: Draft  
**Input**: User description: "Feature: Integrate State Machine into AOF GTO Browser GUI

Problem Statement:
The state machine refactoring is complete and tested, but the new GuiApplication class in aof_gto_browser.py exists as a standalone module. The main application still uses the old aof_gto_browser_gui.py without state machine integration. Users cannot access the improved simulation control functionality.

Current State Analysis:
- aof_gto_browser.py contains the complete state machine implementation with LockedMachine, callbacks, and UI
- aof_gto_browser_gui.py is the current active GUI using basic AoFBrowserPanel
- aof_precompute_runner.py provides the simulation logic that needs to be connected
- No integration between the state machine and actual AOF simulation workflow

Solution Requirements:
Integrate the completed state machine implementation into the main AOF GTO Browser application. Replace the existing GUI with the new state machine-powered interface while preserving existing functionality.

Key Integration Points:
- Replace AoFGTOBrowserGUI with GuiApplication as the main GUI class
- Connect state machine callbacks to AoFPrecomputeRunner for actual simulation execution
- Wire up session management between GuiPrecomputeRunSession and state machine
- Integrate data providers (AoFBrowserDataProvider) with state machine validation
- Preserve existing panel-based UI components and navigation
- Maintain compatibility with existing command-line interface

Success Criteria:
- State machine controls real AOF simulations (not just UI state)
- All existing GUI functionality preserved (browsing, configuration, etc.)
- ThreadPoolExecutor properly managed by state transitions
- Error handling works with actual simulation failures
- Checkpoint/save functionality integrated with state machine
- No regression in existing AOF GTO Browser features

Constraints:
- Must maintain existing python -m hopilot.aof_gto_browser_gui entry point
- Preserve all existing UI components and user workflows
- Ensure backward compatibility with existing data formats
- Keep performance characteristics for real-time simulation control

Research Requirements:
- Analyze aof_gto_browser_gui.py structure and integration points
- Review AoFPrecomputeRunner API for state machine callback integration
- Examine data provider interfaces for validation and session management
- Study existing checkpoint functionality for state machine compatibility"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Replace Main GUI with State Machine (Priority: P1)

As a user of the AOF GTO Browser, I want the main application to use the new state machine interface so that I can access improved simulation control with proper state management.

**Why this priority**: This is the core integration - without replacing the main GUI, users cannot access any of the state machine improvements.

**Independent Test**: Can be fully tested by running the application and verifying the state machine GUI appears with START/PAUSE/RESUME/STOP buttons that respond to state transitions.

**Acceptance Scenarios**:

1. **Given** the application is launched via `python -m hopilot.aof_gto_browser_gui`, **When** the GUI opens, **Then** the new state machine interface is displayed with proper button enablement based on current state
2. **Given** the application is in idle state, **When** user clicks START, **Then** simulation begins and state transitions to running with appropriate UI updates

---

### User Story 2 - Connect State Machine to Simulation Execution (Priority: P1)

As a user running AOF simulations, I want the state machine to control actual simulation processing so that ThreadPoolExecutor and simulation logic work together properly.

**Why this priority**: Essential for the state machine to provide real value - it must control actual simulations, not just UI state.

**Independent Test**: Can be fully tested by starting a simulation through the state machine and verifying that AoFPrecomputeRunner executes real simulation tasks.

**Acceptance Scenarios**:

1. **Given** valid scenario configuration, **When** START is triggered, **Then** AoFPrecomputeRunner creates a session and begins processing simulation cells
2. **Given** simulation is running, **When** PAUSE is triggered, **Then** pending simulation tasks are cancelled and processing stops
3. **Given** simulation is paused with valid context, **When** RESUME is triggered, **Then** processing continues from the previous state

---

### User Story 3 - Integrate Session Management (Priority: P2)

As a user managing long-running simulations, I want session data to be properly tracked and persisted so that simulation progress is maintained across state transitions.

**Why this priority**: Session management is crucial for user experience in long-running simulations, but secondary to basic functionality.

**Independent Test**: Can be fully tested by running a simulation, pausing, and verifying session state is preserved and can be resumed.

**Acceptance Scenarios**:

1. **Given** a simulation session is created, **When** state transitions occur, **Then** GuiPrecomputeRunSession data is updated and persisted appropriately
2. **Given** a paused simulation with saved session, **When** application restarts, **Then** session can be restored and resumed

---

### User Story 4 - Handle Real Simulation Errors (Priority: P2)

As a user running simulations, I want errors during actual processing to be handled gracefully so that I can recover and continue working.

**Why this priority**: Error handling improves reliability but is secondary to core simulation execution.

**Independent Test**: Can be fully tested by triggering simulation errors and verifying proper state transitions and error reporting.

**Acceptance Scenarios**:

1. **Given** simulation encounters a processing error, **When** error occurs, **Then** state machine transitions to failed state and displays error information
2. **Given** system is in failed state, **When** user clicks START, **Then** system resets and allows new simulation

---

### Edge Cases

- What happens when simulation starts but AoFPrecomputeRunner initialization fails?
- How does system handle ThreadPoolExecutor failures during state transitions?
- What happens when session data becomes corrupted during pause/resume?
- How does system behave when multiple rapid state transitions occur?
- What happens when checkpoint functionality conflicts with state machine transitions?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST replace AoFGTOBrowserGUI with GuiApplication as the main GUI class
- **FR-002**: System MUST connect state machine callbacks to AoFPrecomputeRunner for simulation execution
- **FR-003**: System MUST wire GuiPrecomputeRunSession management with state machine transitions
- **FR-004**: System MUST integrate AoFBrowserDataProvider validation with state machine conditions
- **FR-005**: System MUST preserve existing panel-based UI components and navigation structure
- **FR-006**: System MUST maintain the existing `python -m hopilot.aof_gto_browser_gui` command-line entry point
- **FR-007**: System MUST handle real simulation processing errors with proper state transitions
- **FR-008**: System MUST integrate checkpoint/save functionality with state machine persistence
- **FR-009**: System MUST ensure backward compatibility with existing data formats and workflows
- **FR-010**: System MUST preserve performance characteristics for real-time simulation control

### Key Entities *(include if feature involves data)*

- **GuiApplication**: Main GUI class with state machine integration
- **AoFPrecomputeRunner**: Simulation execution engine with session management
- **GuiPrecomputeRunSession**: Session data structure for simulation state
- **AoFBrowserDataProvider**: Data access layer for scenario and result data
- **State Machine**: Transitions library instance managing simulation lifecycle
- **ThreadPoolExecutor**: Concurrent processing pool for simulation tasks

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: State machine successfully controls real AOF simulation execution through AoFPrecomputeRunner
- **SC-002**: All existing GUI functionality (browsing, configuration, panels) is preserved without regression
- **SC-003**: ThreadPoolExecutor lifecycle is properly managed by state machine transitions
- **SC-004**: Error handling works with actual simulation failures and provides clear recovery paths
- **SC-005**: Checkpoint/save functionality integrates seamlessly with state machine persistence
- **SC-006**: No performance degradation in real-time simulation control responsiveness
- **SC-007**: Backward compatibility maintained with existing data formats and user workflows
- **SC-008**: Command-line interface `python -m hopilot.aof_gto_browser_gui` works unchanged

## Assumptions

- AoFPrecomputeRunner API is compatible with state machine callback integration
- Existing UI components can be adapted to work within the new GuiApplication structure
- Session data structures are compatible between GuiPrecomputeRunSession and state machine
- Data provider interfaces support the required validation and error handling

## Dependencies

- Completed state machine implementation in `aof_gto_browser.py`
- Existing AoFPrecomputeRunner and related simulation infrastructure
- AoFBrowserDataProvider and data access components
- Existing checkpoint/save functionality

## Out of Scope

- Changes to simulation algorithms or processing logic
- New UI components or interface redesign
- Database schema modifications
- Performance optimizations beyond integration requirements

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

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]
