# Implementation Plan: Test Suite Cleanup

**Branch**: `001-test-suite-cleanup` | **Date**: 2026-04-01 | **Spec**: [specs/001-test-suite-cleanup/spec.md](specs/001-test-suite-cleanup/spec.md)
**Status**: Phase 1 Complete - Ready for Implementation
**Input**: Feature specification from `/specs/001-test-suite-cleanup/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Clean up nonsensical and fake tests in the poker analysis tool test suite by rewriting placeholder tests, replacing meaningless assertions, fixing tests expecting deterministic results from random behavior, and enhancing existence-only tests to validate actual functionality rather than mocks or artificial constructs.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

## Technical Context

**Language/Version**: Python 3.x  
**Primary Dependencies**: pytest, unittest.mock  
**Storage**: SQLite databases (for test data persistence)  
**Testing**: pytest with in-memory databases  
**Target Platform**: Windows (PowerShell environment)  
**Project Type**: Test suite maintenance (existing desktop application)  
**Performance Goals**: N/A (test cleanup, not performance-critical)  
**Constraints**: Tests must be simple, straightforward, self-documenting; mocks largely unnecessary  
**Scale/Scope**: 9 specific test issues across 6 test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle VI (Comprehensive Testing)**: ✅ PASS - This feature improves test quality and coverage by cleaning up nonsensical tests.

**Principle XII (Quality Assurance)**: ✅ PASS - This feature directly implements the Quality Assurance principle by removing fake tests and ensuring genuine test validation.

**Testing Directory Structure**: ✅ PASS - All test modifications will maintain the required root `tests/` directory structure.

**Additional Requirements**: ✅ PASS - Test cleanup maintains pytest usage and proper test organization.

**Post-Design Evaluation**: ✅ PASS - Design artifacts maintain constitution compliance:
- No new data models introduced (maintains existing structure)
- Test contracts align with Quality Assurance principle
- Quickstart guide promotes proper TDD practices
- Agent context updated with relevant technologies

**Gate Status**: ✅ ALL GATES PASS - No violations detected. Feature aligns with constitution principles.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

## Project Structure

### Documentation (this feature)

```text
specs/001-test-suite-cleanup/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
tests/
├── test_models.py                    # FR-001: Rewrite test_table_creation
├── test_aof_gui_precompute_runner_canonical_dedup.py  # FR-002: Rewrite deduplication tests
├── test_all_in_fold_gto.py          # FR-003: Rewrite GTO threshold test
├── test_db_browser_integration.py   # FR-004: Replace assert True statements
├── test_incremental_aggregation.py  # FR-005: Replace assert True statement
├── test_jackpot_metrics.py          # FR-006: Fix random behavior expectations
├── test_aof_browser_panel_database_integration.py  # FR-007: Enhance payload validation
├── test_aggregation_engine_comprehensive.py  # FR-008: Replace existence checks
└── test_browser_database_provider_persistence.py  # FR-009: Complete assertions
```

**Structure Decision**: Working with existing test files in the root `tests/` directory as required by constitution. No new files created, only modifications to existing test files.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
