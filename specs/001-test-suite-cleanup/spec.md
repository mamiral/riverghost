# Feature Specification: Test Suite Cleanup

**Feature Branch**: `001-test-suite-cleanup`  
**Created**: 2026-03-29  
**Status**: Draft  
**Input**: User description: "Create a feature specification for cleaning up nonsensical and fake tests in the poker analysis tool test suite. The tests to be addressed include: Fake/placeholder tests that need removal or proper implementation: 1. test_models.py::test_table_creation - contains only pass 2. test_aof_gui_precompute_runner_canonical_dedup.py - tests with TODO comments indicating they need to be rewritten to remove mocks and test actual deduplication logic 3. test_all_in_fold_gto.py::test_find_gto_threshold_basic_functionality - mocks internal methods with placeholder comment about implementation being incomplete Tests with meaningless assertions: 4. test_db_browser_integration.py - multiple assert True statements (lines 175, 211, 340, 370, 399, 593, 662) 5. test_incremental_aggregation.py - assert True at line 157 Tests expecting deterministic results from random behavior: 6. test_jackpot_metrics.py::test_calculate_cell_equity - expects fixed 0.6 equity from random win determination Tests checking only basic existence without functionality: 7. test_aof_browser_panel_database_integration.py - multiple tests only checking panel.payload is not None with mocked databases 8. test_aggregation_engine_comprehensive.py - multiple assert result is not None checks without content validation 9. test_browser_database_provider_persistence.py - incomplete assertions missing content checks The specification should define tasks to either remove these nonsensical tests entirely or rewrite them to properly test actual implementation behavior rather than mocks or placeholders. Focus on ensuring tests validate real functionality, not just that methods can be called or mocks return values. It is ok if the tests are failing at the end of this feature – it is even expected because the implementation is missing, and will be added in the subsequent features."

## Clarifications

### Session 2026-04-01
- Q: When should tests be removed entirely vs. rewritten? Should we have a general rule or decide case-by-case? For example, should placeholder tests always be removed, while mock-heavy tests get rewritten → A: Placeholder tests should be rewritten to fail, mock-heavy tests need to be rewritten. otherwise we decide case-by-case
- Q: What are the acceptable performance constraints for the cleaned-up tests? Should tests run within certain time limits, and how should we handle tests that require significant setup time → A: no. we have long running tests already.
- Q: What specific maintainability requirements should the rewritten tests follow? For example, should tests be self-documenting, follow naming conventions, or have specific complexity limits → A: the tests should be simple and straightforward and self-documenting. mocks should largely be not needed.
- Q: What additional edge cases should be considered for test failure handling? For example, how should tests behave when databases are unavailable, external services fail, or when test data is corrupted → A: tests fail and report failure reason
- Q: What tradeoffs should be considered between test completeness and implementation availability? Should we create stub implementations for missing functionality, or keep tests failing until real code is → A: tests fail until implementation is complete. this is the red phase.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove Placeholder Tests (Priority: P1)

As a developer maintaining the test suite, I want to identify and remove tests that contain only placeholder code (like `pass` statements) so that the test suite accurately reflects the system's test coverage and doesn't include meaningless entries.

**Why this priority**: Placeholder tests provide false confidence in test coverage and can mask real issues. Removing them first establishes a clean baseline.

**Independent Test**: Can be tested by running the test suite and verifying that removed tests no longer appear in test output, and that no new failures are introduced in remaining tests.

**Acceptance Scenarios**:

1. **Given** test_models.py::test_table_creation contains only `pass`, **When** the test is removed, **Then** the test no longer exists in the codebase and pytest doesn't attempt to run it
2. **Given** tests with TODO comments indicating incomplete implementation, **When** these tests are removed, **Then** the codebase no longer contains placeholder test code

---

### User Story 2 - Rewrite Meaningless Assertions (Priority: P2)

As a developer running tests, I want tests to contain meaningful assertions that validate actual functionality rather than trivial `assert True` statements, so that test failures indicate real problems rather than placeholder code.

**Why this priority**: Meaningless assertions waste developer time during debugging and provide no value in catching regressions.

**Independent Test**: Can be tested by running individual test methods and verifying they fail when expected conditions are not met, and pass when functionality works correctly.

**Acceptance Scenarios**:

1. **Given** test_db_browser_integration.py has `assert True` at lines 175, 211, 340, 370, 399, 593, 662, **When** these assertions are replaced with meaningful checks, **Then** the tests validate actual database integration behavior
2. **Given** test_incremental_aggregation.py has `assert True` at line 157, **When** the assertion is replaced, **Then** the test validates incremental aggregation logic

---

### User Story 3 - Fix Tests Expecting Deterministic Results from Random Behavior (Priority: P2)

As a developer testing random or probabilistic functionality, I want tests to properly handle non-deterministic behavior rather than expecting fixed results, so that tests are reliable and don't fail randomly.

**Why this priority**: Tests expecting deterministic results from random behavior cause flaky test suites and reduce confidence in test results.

**Independent Test**: Can be tested by running the test multiple times and verifying it passes consistently, while still validating the underlying logic.

**Acceptance Scenarios**:

1. **Given** test_jackpot_metrics.py::test_calculate_cell_equity expects fixed 0.6 equity, **When** the test is rewritten to handle random win determination properly, **Then** the test validates equity calculation logic without expecting specific random outcomes

---

### User Story 4 - Enhance Existence-Only Tests (Priority: P3)

As a developer verifying system components, I want tests to validate actual content and functionality rather than just checking that objects exist, so that tests catch real integration issues.

**Why this priority**: Existence-only tests provide minimal value and can pass even when functionality is broken.

**Independent Test**: Can be tested by modifying the underlying implementation to return invalid data and verifying the tests fail appropriately.

**Acceptance Scenarios**:

1. **Given** test_aof_browser_panel_database_integration.py only checks `panel.payload is not None`, **When** the tests are enhanced, **Then** they validate actual payload content and database integration
2. **Given** test_aggregation_engine_comprehensive.py has `assert result is not None` checks, **When** these are replaced, **Then** tests validate aggregation results content
3. **Given** test_browser_database_provider_persistence.py has incomplete assertions, **When** they are completed, **Then** tests validate persistence behavior comprehensively

---

### User Story 5 - Remove Mock-Heavy Tests (Priority: P3)

As a developer testing system behavior, I want tests to validate real implementation rather than mocked interactions, so that tests catch integration issues and validate end-to-end functionality.

**Why this priority**: Mock-heavy tests can pass even when the real implementation is broken, reducing test effectiveness.

**Independent Test**: Can be tested by running tests against actual implementations and verifying they exercise real code paths.

**Acceptance Scenarios**:

1. **Given** test_aof_gui_precompute_runner_canonical_dedup.py uses mocks for deduplication logic, **When** tests are rewritten, **Then** they test actual deduplication implementation
2. **Given** test_all_in_fold_gto.py::test_find_gto_threshold_basic_functionality mocks internal methods, **When** the test is rewritten, **Then** it validates real GTO threshold finding logic

### Edge Cases

- What happens when removing a test that was referenced in CI/CD pipelines?
- How does system handle tests that depend on external services or databases?
- What happens when rewritten tests reveal previously hidden bugs in implementation?
- Tests MUST fail and report failure reasons when databases are unavailable
- Tests MUST fail and report failure reasons when external services fail
- Tests MUST fail and report failure reasons when test data is corrupted

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST rewrite test_models.py::test_table_creation to fail meaningfully instead of containing only a `pass` statement
- **FR-002**: System MUST rewrite tests in test_aof_gui_precompute_runner_canonical_dedup.py to remove mocks and test actual deduplication logic instead of using TODO comments
- **FR-003**: System MUST rewrite test_all_in_fold_gto.py::test_find_gto_threshold_basic_functionality to test real GTO threshold finding logic instead of mocking internal methods
- **FR-004**: System MUST replace all `assert True` statements in test_db_browser_integration.py (lines 175, 211, 340, 370, 399, 593, 662) with meaningful assertions validating database integration behavior
- **FR-005**: System MUST replace the `assert True` statement in test_incremental_aggregation.py (line 157) with meaningful validation of incremental aggregation functionality
- **FR-006**: System MUST rewrite test_jackpot_metrics.py::test_calculate_cell_equity to properly handle random win determination without expecting fixed 0.6 equity results
- **FR-007**: System MUST enhance tests in test_aof_browser_panel_database_integration.py to validate payload content beyond `panel.payload is not None` checks
- **FR-008**: System MUST replace `assert result is not None` checks in test_aggregation_engine_comprehensive.py with content validation of aggregation results
- **FR-009**: System MUST complete incomplete assertions in test_browser_database_provider_persistence.py to include content validation for persistence behavior
- **FR-010**: All rewritten tests MUST validate actual implementation behavior rather than mock interactions
- **FR-011**: All tests MUST avoid expecting deterministic results from random or probabilistic behavior
- **FR-012**: All rewritten tests MUST be simple, straightforward, self-documenting, and largely avoid mocks
- **FR-013**: Tests MUST fail and report failure reasons when encountering edge cases like unavailable databases or corrupted test data

### Key Entities *(include if feature involves data)*

- **Test File**: Represents individual test files in the test suite, containing test methods and assertions
- **Test Case**: Represents individual test methods within test files, with specific assertions and validation logic
- **Test Assertion**: Represents individual validation statements within test cases, checking expected vs actual behavior

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All specified nonsensical tests are either removed entirely or rewritten to validate real functionality, with 0 remaining `assert True` statements
- **SC-002**: Test suite contains no tests expecting deterministic results from random behavior
- **SC-003**: All tests validate content and functionality rather than just object existence
- **SC-004**: No tests rely on mocks to validate core business logic implementation
- **SC-005**: Test suite execution completes without random failures due to improper handling of non-deterministic behavior

## Assumptions

- Implementation bugs revealed by rewritten tests will be addressed in subsequent features
- Test failures are expected and acceptable as they indicate missing or broken implementation (this is the "red phase" of TDD)
- External dependencies and databases required for testing are available during test execution
- Tests will fail until implementation is complete, following red-green-refactor cycle
