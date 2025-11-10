# Tasks: Environment Setup

## Phase 1: Setup

- [X] T001 Create project directory at ~/matija/riverghost
- [ ] T002 Install system dependencies with apt (`wine`, `winetricks`, `python3-pip`, `pipenv`, `libevdev2`, `x11-utils`, `python3-evdev`)
- [ ] T002.1 Load uinput kernel module, set permissions with udev rule, and add user to input group for /dev/uinput access
- [ ] T003 Set up dedicated WINEPREFIX at ~/matija/riverghost/.wine-riverghost and export WINEPREFIX
- [ ] T004 Download WPTClient.exe to ~/Downloads
- [ ] T005 Install WPT client using Wine (`wine ~/Downloads/WPTClient.exe`)
- [ ] T006 Set up Wine with .NET and VC runtimes (`winetricks dotnet48 vcrun2022`)
- [ ] T007 [P] Install pipenv using apt or pip (`pip install --user pipenv`)
- [ ] T008 [P] Initialize pipenv environment in ~/matija/riverghost (`pipenv install --python 3.12`)
- [ ] T009 [P] Install Python dependencies in pipenv (`pipenv install ultralytics mss opencv-python easyocr evdev pypoker-eval ollama numpy asyncio schedule humanize noise label-studio`)
- [ ] T010 [P] Activate pipenv shell in ~/matija/riverghost (`pipenv shell`)

## Phase 2: Foundational

- [ ] T011 Verify WPT client launches (`wine WPTClient.exe`)
- [ ] T012 Verify Python stack (`pipenv run python -c "import mss; print('OK')"`)
- [ ] T013 Document troubleshooting steps in setup_guide.md

## Phase 3: User Stories

### User Story 1 - Complete Environment Setup (Priority: P1)

- [ ] T014 [US1] Confirm all setup steps are independently testable per guide
- [ ] T015 [US1] Validate that both WPT client and Python environment are operational

### User Story 2 - Dependency Troubleshooting (Priority: P2)

- [ ] T016 [US2] Simulate missing dependency and verify guide enables recovery

## Final Phase: Polish & Cross-Cutting

- [ ] T017 Review and update setup_guide.md for clarity and completeness

## Dependencies

- Phase 1 tasks must be completed before Phase 2.
- User Story 1 and 2 tasks can be executed in parallel after foundational tasks.

## Parallel Execution Examples

- T006, T007, T008, and T009 can be run in parallel after T005.
- T013 and T014 can be executed in parallel after foundational verification.

## Implementation Strategy

- MVP: Complete all Phase 1 and Phase 2 tasks, plus User Story 1.
- Incremental delivery: Add troubleshooting and polish tasks as issues are discovered.
