# Feature Specification: Environment Setup

**Feature Branch**: `1-env-setup`  
**Created**: 2025-11-05  
**Status**: Draft  
**Input**: User description: "analyze documentation in `docs/initial_design` dir and create specification for `PHASE 1: ENVIRONMENT SETUP`. also create a setup guide document describing how to set it up from vanilla ubuntu installation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Environment Setup (Priority: P1)

A user wants to set up the Riverghost development environment from scratch on a clean Ubuntu 24.04 LTS system, including all dependencies and the WPT client.

**Why this priority**: This is the foundational step required for all subsequent development and testing.

**Independent Test**: Can be fully tested by following the setup guide and verifying that both the WPT client and Python environment are operational.

**Acceptance Scenarios**:

1. **Given** a clean Ubuntu 24.04 LTS system, **When** the user follows the setup guide, **Then** the WPT client launches successfully under Wine and Python dependencies are installed and importable.
2. **Given** the environment is set up, **When** running `wine WPTClient.exe` and `python -c "import mss; print('OK')"` **Then** both commands succeed without errors.

---

### User Story 2 - Dependency Troubleshooting (Priority: P2)

A user encounters an error during installation (e.g., missing system package or Wine component) and needs to resolve it using the guide.

**Why this priority**: Ensures the setup process is robust and accessible to users with varying levels of experience.

**Independent Test**: Can be tested by intentionally omitting a step and verifying the guide provides enough information to recover.

**Acceptance Scenarios**:

1. **Given** a missing dependency, **When** the user consults the guide, **Then** they can identify and install the missing component.

---

### Edge Cases

- What happens if a required package is unavailable or fails to install?
- How does the system handle Wine or .NET installation errors?
- What if the user is running on a non-Ubuntu or older Ubuntu version?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a step-by-step guide for setting up the environment on Ubuntu 24.04 LTS.
- **FR-002**: System MUST specify all required system and Python dependencies.
- **FR-003**: Users MUST be able to install and launch the WPT client under Wine.
- **FR-004**: System MUST enable creation and activation of a Python virtual environment using pipenv.
- **FR-005**: Users MUST be able to verify the installation by running provided test commands.
- **FR-006**: System MUST document troubleshooting steps for common setup issues.

### Key Entities

- **Environment Setup Guide**: Document outlining all steps, commands, and verification checks for initial setup.
- **System Dependencies**: List of required Ubuntu packages and Wine components.
- **Python Environment**: Virtual environment with all required Python packages.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete the full environment setup in under 30 minutes.
- **SC-002**: 100% of users can launch the WPT client and import all Python dependencies after following the guide.
- **SC-003**: All required commands complete without errors on a clean Ubuntu 24.04 LTS installation.
- **SC-004**: Troubleshooting section resolves at least 90% of common setup issues without external support.

## Assumptions

- User has access to Ubuntu 24.04 LTS (desktop or VM).
- User can download the WPT client installer (`WPTClient.exe`).
- Internet connection is available for package installation.
- No conflicting Python or Wine installations are present.
