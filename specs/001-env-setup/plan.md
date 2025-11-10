# Implementation Plan: Environment Setup

**Branch**: `001-env-setup` | **Date**: 2025-11-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-env-setup/spec.md`

## Summary

Set up a reproducible, isolated Python development environment for Riverghost on Ubuntu 24.04 LTS, including all system and Python dependencies, WPT client under Wine, and pipenv-based workflow. All steps and requirements are documented in the setup guide.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: pipenv, ultralytics, mss, opencv-python, easyocr, evdev, python3-evdev, pypoker-eval, ollama, numpy, asyncio, schedule, humanize, noise, label-studio
**Storage**: N/A  
**Testing**: Manual verification, `pipenv run python -c "import mss; print('OK')"`  
**Target Platform**: Ubuntu 24.04 LTS (desktop or VM), Wine  
**Project Type**: Single-project CLI/automation  
**Performance Goals**: Setup completes in under 30 minutes  
**Constraints**: 100% offline, pipenv for all Python code, no data uploads
**System Setup**: uinput kernel module is built-in on Ubuntu 24.04; load with `modprobe uinput`. Set permissions with udev rule and add user to input group for /dev/uinput access. Remove any reference to uinput-modules-dkms.
**Scale/Scope**: Single-user, local workstation

## Constitution Check

- 100% offline operation: All steps are local, no uploads.
- Human-like input: Not applicable for environment setup.
- Update resilience: Not applicable for environment setup.
- Modular, testable, documented: Setup guide and spec are clear and testable.
- Python environment: pipenv is required and enforced.
- Reuse & minimal implementation: Uses standard Ubuntu and Python tooling.

## Project Structure

### Documentation (this feature)

```text
specs/001-env-setup/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/
```

**Structure Decision**: Single CLI/automation project, no web/mobile split.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
