# Research Phase 0: Test Suite Cleanup

**Date**: 2026-04-01
**Status**: Complete - No unknowns requiring research

## Research Tasks

### Task 1: Analyze Current Test Implementations
**Status**: ✅ Complete  
**Finding**: All target test files exist and have been reviewed. The specific issues identified in the spec are accurate and actionable.

**Details**:
- `test_models.py::test_table_creation`: Contains only `pass` statement
- `test_aof_gui_precompute_runner_canonical_dedup.py`: Has TODO comments about mock removal
- `test_all_in_fold_gto.py::test_find_gto_threshold_basic_functionality`: Mocks internal methods
- `test_db_browser_integration.py`: Multiple `assert True` statements at specified lines
- `test_incremental_aggregation.py`: `assert True` at line 157
- `test_jackpot_metrics.py::test_calculate_cell_equity`: Expects fixed 0.6 equity from random behavior
- `test_aof_browser_panel_database_integration.py`: Only checks `panel.payload is not None`
- `test_aggregation_engine_comprehensive.py`: Multiple `assert result is not None` checks
- `test_browser_database_provider_persistence.py`: Incomplete assertions

### Task 2: Determine Proper Test Behavior
**Status**: ✅ Complete  
**Finding**: Tests should follow TDD red phase - fail initially until implementation is complete. No specific research needed as behavior is defined by constitution Principle XII.

**Details**:
- Placeholder tests: Rewrite to fail meaningfully (not remove)
- Mock-heavy tests: Rewrite to test real implementation
- Random behavior: Handle probabilistically without fixed expectations
- Existence checks: Replace with content validation
- Meaningless assertions: Replace with functional validation

### Task 3: Validate Technical Approach
**Status**: ✅ Complete  
**Finding**: Technical context is well-defined. Python/pytest environment with SQLite databases for testing. No additional research required.

**Details**:
- Language: Python 3.x ✅
- Testing framework: pytest ✅  
- Storage: SQLite databases ✅
- Platform: Windows ✅
- Constraints: Simple, self-documenting tests ✅

## Decisions

### Decision 1: Test Rewrite Strategy
**Chosen**: Follow clarified constitution guidance - rewrite placeholder tests to fail meaningfully, rewrite mock-heavy tests to test real implementation, ensure tests are simple and self-documenting.

**Rationale**: Aligns with Quality Assurance principle and clarified requirements from specification.

**Alternatives Considered**:
- Remove placeholder tests entirely: Rejected per clarification
- Keep mock-heavy tests: Rejected per constitution

### Decision 2: Random Behavior Testing
**Chosen**: Remove fixed expectations (like 0.6 equity) and implement proper probabilistic validation.

**Rationale**: Constitution prohibits expecting deterministic results from random behavior.

**Alternatives Considered**:
- Keep fixed expectations: Rejected per constitution
- Remove random tests entirely: Rejected as functionality needs testing

### Decision 3: Failure Handling
**Chosen**: Tests fail and report specific failure reasons for edge cases.

**Rationale**: Aligns with clarified requirements for proper error reporting.

## Research Summary

**No external research required** - All information needed is available in existing codebase and constitution. The feature involves modifying existing test files with known issues, using established pytest patterns and Python testing practices.

**Phase 0 Complete**: ✅ All unknowns resolved. Ready for Phase 1 design.