# Feature Specification: Refactor GuiRunState State Machine Using Transitions Library

**Feature Branch**: `001-gui-state-refactor`  
**Created**: March 18, 2026  
**Status**: Draft  
**Input**: User description: "Feature: Refactor GuiRunState State Machine Using Transitions Library

Problem Statement:
The current GuiRunState state machine implementation in the AOF GTO Browser has critical flaws in state management and control flow logic. Key issues include:

Inconsistent state transitions (e.g., STOP from PAUSED directly resets session without proper cleanup)
Scattered button enablement logic that creates UI/state mismatches
Improper handling of ThreadPoolExecutor lifecycle during state changes
Context validation blocking legitimate resume operations
No single source of truth for allowed operations
These issues lead to unreliable simulation control, potential resource leaks, and poor user experience.

Current State Analysis:
The existing state machine uses a basic enum-based approach with manual transition logic. States include IDLE, RUNNING, PAUSED, STOPPING, COMPLETED, and FAILED. Button handlers contain complex conditional logic for state validation and transitions, making the code fragile and hard to maintain.

Solution Requirements:
Replace the flawed manual state machine with a robust implementation using the transitions (version 0.9.3) Python state machine library. The new implementation must leverage the library's advanced features:

State Definition: Define clear, well-documented states with proper on_enter/on_exit callbacks for resource management
Transition Logic: Implement clean transitions with appropriate conditions, before/after callbacks, and error handling using on_exception and finalize_event
Button Integration: Centralize button enablement logic based on current state using get_triggers() and may_<trigger>() methods
Resource Management: Properly handle ThreadPoolExecutor lifecycle in state callbacks with proper cleanup in on_exit
Context Validation: Implement intelligent resume logic using conditional transitions and unless parameters
Error Handling: Provide robust error states and recovery mechanisms using on_exception callbacks and queued transitions for thread safety
Research Requirements:
Before implementation planning, thoroughly analyze the transitions library source code in the transitions directory to establish best practices:

Review the core Machine class in transitions/core.py for state/transition management and callback execution order
Study callback execution patterns: prepare → conditions → before → on_exit → on_enter → after → finalize_event
Examine threading extensions for concurrent operation handling with Pygame GUI integration
Analyze examples in examples for real-world patterns, especially queued transitions for thread safety
Review documentation in README.md for advanced features like conditional transitions, event data passing with send_event=True, and internal transitions
Identify optimal patterns for integrating with Pygame GUI event handling using trigger() method
Determine best practices for state persistence and restoration using model serialization
Evaluate AsyncMachine or LockedMachine extensions for thread-safe GUI operations
Success Criteria:

All identified issues from the analysis document are resolved
State machine behavior matches the proposed diagrams in simulation_control_logic_analysis.md
Code is more maintainable and testable using may_<trigger>() for validation
Thread safety is preserved for GUI operations using queued transitions
Backward compatibility with existing checkpoint/save functionality
Proper resource cleanup verified through state exit callbacks
Constraints:

Must use transitions==0.9.3 (already available in project)
Maintain existing GUI integration patterns using send_event=True for data passing
Preserve performance characteristics for real-time simulation control
Ensure compatibility with Pygame threading model using appropriate extensions
Leverage library's built-in transition validation instead of manual checks"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start Precompute Simulation (Priority: P1)

As a user of the AOF GTO Browser, I want to start a precompute simulation so that I can analyze poker scenarios in the background.

**Why this priority**: This is the primary functionality of the application - starting simulations is the core user action.

**Independent Test**: Can be fully tested by clicking START button and verifying simulation begins, UI updates correctly, and background processing starts.

**Acceptance Scenarios**:

1. **Given** the application is in idle state with a valid scenario loaded, **When** user clicks START button, **Then** simulation begins, UI shows running state, and ThreadPoolExecutor starts processing cells
2. **Given** the application is in completed or failed state, **When** user clicks START button, **Then** system resets to idle and starts new simulation

---

### User Story 2 - Pause and Resume Simulation (Priority: P1)

As a user of the AOF GTO Browser, I want to pause and resume simulations so that I can temporarily halt processing when needed.

**Why this priority**: Essential control functionality for long-running simulations - users need to be able to pause for various reasons.

**Independent Test**: Can be fully tested by starting simulation, pausing, verifying processing stops, then resuming and verifying processing continues.

**Acceptance Scenarios**:

1. **Given** simulation is running, **When** user clicks PAUSE button, **Then** processing stops, futures are cancelled, and UI shows paused state
2. **Given** simulation is paused with matching context, **When** user clicks RESUME button, **Then** new executor starts and processing continues
3. **Given** simulation is paused with changed context, **When** user clicks RESUME button, **Then** resume is blocked with appropriate error message

---

### User Story 3 - Stop Simulation (Priority: P1)

As a user of the AOF GTO Browser, I want to stop simulations so that I can end processing and reset the session.

**Why this priority**: Critical for ending simulations and cleaning up resources - users need full control over simulation lifecycle.

**Independent Test**: Can be fully tested by starting simulation, stopping, and verifying all resources are cleaned up and session is reset.

**Acceptance Scenarios**:

1. **Given** simulation is running or paused, **When** user clicks STOP button, **Then** processing stops gracefully, resources are cleaned up, and system returns to idle state
2. **Given** simulation encounters an error, **When** system handles the error, **Then** it transitions to failed state and allows restart

---

### User Story 4 - Handle Simulation Errors Gracefully (Priority: P2)

As a user of the AOF GTO Browser, I want the system to handle errors during simulation so that I can recover and continue working.

**Why this priority**: Error handling is important for reliability but secondary to core functionality.

**Independent Test**: Can be fully tested by simulating errors during processing and verifying proper state transitions and error reporting.

**Acceptance Scenarios**:

1. **Given** simulation encounters an error during processing, **When** error occurs, **Then** system transitions to failed state and provides error feedback
2. **Given** system is in failed state, **When** user clicks START, **Then** system resets and allows new simulation

---

### Edge Cases

- What happens when user rapidly clicks buttons during state transitions?
- How does system handle ThreadPoolExecutor shutdown during critical operations?
- What happens when context validation fails during resume?
- How does system behave when disk space is low during checkpointing?
- What happens when multiple GUI events occur simultaneously?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement state machine using transitions library with proper state definitions and transitions
- **FR-002**: System MUST provide START button functionality to initiate simulations from idle/completed/failed states
- **FR-003**: System MUST provide PAUSE button functionality to halt running simulations
- **FR-004**: System MUST provide RESUME button functionality with context validation
- **FR-005**: System MUST provide STOP button functionality to gracefully end simulations
- **FR-006**: System MUST handle ThreadPoolExecutor lifecycle properly in state transitions
- **FR-007**: System MUST centralize button enablement logic based on current state
- **FR-008**: System MUST implement proper error handling and recovery mechanisms
- **FR-009**: System MUST maintain backward compatibility with existing checkpoint functionality
- **FR-010**: System MUST preserve thread safety for GUI operations

### Key Entities *(include if feature involves data)*

- **State Machine**: Core transitions Machine instance managing simulation states
- **Simulation States**: IDLE, RUNNING, PAUSED, STOPPING, COMPLETED, FAILED states with callbacks
- **Transitions**: Triggered state changes with conditions and callbacks
- **ThreadPoolExecutor**: Managed resource for background processing
- **Session Context**: Simulation parameters and state data
- **GUI Buttons**: START, PAUSE, RESUME, STOP with state-dependent enablement

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All identified issues from simulation_control_logic_analysis.md are resolved without introducing new issues
- **SC-002**: State machine behavior matches proposed diagrams in simulation_control_logic_analysis.md
- **SC-003**: Code maintainability improves with centralized state logic and reduced conditional complexity
- **SC-004**: Thread safety is preserved with no race conditions in GUI operations
- **SC-005**: Backward compatibility maintained with existing checkpoint/save functionality
- **SC-006**: Resource cleanup verified through proper state exit callbacks and no memory leaks
- **SC-007**: Button enablement logic is centralized and consistent across all UI states
- **SC-008**: Error handling provides clear feedback and allows recovery without application restart

## Assumptions

- Transitions library version 0.9.3 provides all necessary features for implementation
- Existing GUI framework (Pygame) is compatible with transitions library integration
- Current simulation logic can be adapted to work with new state machine callbacks
- ThreadPoolExecutor usage patterns remain compatible with new state management

## Dependencies

- transitions==0.9.3 (availability needs to be confirmed; otherwise install it)
- Existing AOF GTO Browser GUI components
- Current simulation processing logic
- Checkpoint/save functionality

## Out of Scope

- Changes to simulation algorithms or processing logic
- GUI redesign or new UI components
- Database schema modifications
- Performance optimizations beyond state machine requirements
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
