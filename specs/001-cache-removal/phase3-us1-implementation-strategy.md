# Phase 3 US1 Implementation Strategy: GUI Database Refactoring

**Feature**: 001-cache-removal | **Phase**: 3 | **User Story**: US1 (GUI Displays Current Database State)

**Tasks**: T014-T021 | **Priority**: P1

---

## Refactoring Strategy

### Current State (Cache-Based)
```python
# aof_browser_panel.py - CURRENT (using cache provider)
from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider

class AoFBrowserPanel:
    def __init__(self, fixture_path, database_url):
        self.provider = AoFBrowserDataProvider(
            fixture_path=fixture_path, 
            database_url=database_url
        )
    
    def load_matrix(self, position, action):
        # Queries cache (fallback to persistent cache DB)
        self.payload = self.provider.get_matrix_payload(
            position=position,
            action=action
        )
```

### Target State (Database-Based)

```python
# aof_browser_panel.py - TARGET (using direct database queries)
from hopilot import db
from hopilot.gto.normalized_db_provider import get_strategy_matrix_from_db

class AoFBrowserPanel:
    def __init__(self, database_url):
        # No provider; use database directly
        self.database_url = database_url
    
    def load_matrix(self, position, action):
        # Direct database query
        try:
            with db.session_context() as session:
                self.payload = get_strategy_matrix_from_db(
                    session=session,
                    position=position,
                    action=action
                )
        except DatabaseError:
            # Show "no data" gracefully
            self.show_error("No strategy data available")
            self.payload = None
```

---

## Task Breakdown & Implementation Sequence

### T014: Remove In-Memory Cache Dict Usage
**Status**: Preparation

**Action**: Mark `self._cache` dict as deprecated in AoFBrowserDataProvider
- Add deprecation warning when cache is accessed
- Document: "Cache will be removed in Phase 4; use DatabaseProvider instead"
- Keep functioning for backward compatibility during refactoring

**Impact**: Signals to GUI that cache should not be relied upon

---

### T015: Replace Cache Lookup with Database Query Method
**Status**: Create database query interface

**Action** in `aof_browser_data_provider.py`:
1. Add new method `get_matrix_from_database()` that:
   - Accepts `session` (SQLAlchemy session)
   - Queries `HandMatrix` model for position/action combo
   - Returns structured payload matching old format
   - No caching

**Code Pattern**:
```python
def get_matrix_from_database(self, session, position, action):
    """Get matrix from database - no cache fallback."""
    try:
        matrix = session.query(HandMatrix).filter(
            HandMatrix.position == position,
            HandMatrix.action == action
        ).first()
        
        if not matrix:
            return {"status": "MISSING", "cells": []}
        
        # Hydrate to match legacy payload format
        return self._hydrate_matrix_payload(matrix)
    except Exception as e:
        self.logger.error(f"Database query failed: {e}")
        return {"status": "ERROR", "error": str(e)}
```

---

### T016: Refactor AoFBrowserPanel to Query Database
**Status**: GUI refactoring (sample)

**Action**: Modify GUI to:
1. Replace `self.provider.get_matrix_payload()` calls with database queries
2. Catch `DatabaseError` and show graceful "no data" message
3. Remove cache validation checks (T018)

**Sample Refactoring**:
```python
# OLD (cache-based)
def load_matrix(self, position, action):
    self.payload = self.provider.get_matrix_payload(position, action)
    self.display_matrix(self.payload)

# NEW (database-based)
def load_matrix(self, position, action):
    try:
        with db.session_context() as session:
            matrix = session.query(HandMatrix).filter(
                HandMatrix.position == position,
                HandMatrix.action == action
            ).first()
            
            if not matrix:
                self.show_error("No strategy data for this position/action")
                return
            
            self.payload = self._format_matrix_for_display(matrix)
            self.display_matrix(self.payload)
    except Exception as e:
        self.logger.error(f"Failed to load matrix: {e}")
        self.show_error(f"Database error: {e}")
```

---

### T017: Create Database Query Helper
**Status**: Create `normalized_db_provider.py` helper functions

**Functions to implement**:
```python
def get_strategy_matrix_from_db(session, position, action):
    """
    Query database for strategy matrix.
    
    Args:
        session: SQLAlchemy session
        position: Position ID (e.g., "UTG", "BTN")
        action: Action ID (e.g., "open_raise", "call")
    
    Returns:
        StrategyMatrix model instance or None
    """
    return session.query(HandMatrix).filter(
        HandMatrix.position == position,
        HandMatrix.action == action
    ).first()

def get_hand_equity_from_db(session, matrix_id, hand_id):
    """Get individual hand equity from matrix."""
    return session.query(MatrixCell).filter(
        MatrixCell.hand_matrix_id == matrix_id,
        MatrixCell.hand_id == hand_id
    ).first()
```

---

### T018: Update State Machine (Remove Cache Checks)
**Status**: Cleanup cache validation

Remove all cache-related state machine transitions:
- Remove `cache_valid` checks from `state_machine_controller.py`
- Remove cache invalidation triggers
- Keep precompute completion logic

---

### T019: Add Database Error Handling
**Status**: Graceful error messages

Add GUI error display for database failures:
```python
def show_error(self, message):
    """Display error in GUI instead of crashing."""
    self.status_label.setText(f"Error: {message}")
    self.matrix_display.clear()
```

---

### T020: Create Integration Test
**Status**: Test pattern

```python
def test_gui_loads_matrix_from_database():
    """Test: GUI displays data correctly from database."""
    # Setup
    with session_context() as session:
        matrix = factory.create_hand_matrix(
            session, 
            position="UTG", 
            action="open_raise"
        )
    
    # Execute
    panel = AoFBrowserPanel(database_url=test_db_url)
    panel.load_matrix("UTG", "open_raise")
    
    # Assert
    assert panel.payload is not None
    assert panel.payload["position"] == "UTG"
    assert len(panel.payload["cells"]) == 169
```

---

### T021: Document Matrix Payload Structure
**Status**: API documentation

Map database models to legacy payload format for GUI compatibility.

---

## Refactoring Complexity Assessment

**Total Files to Modify**: ~3 core files
- `aof_browser_data_provider.py` (add helper method)
- `aof_browser_panel.py` (replace cache calls with DB queries)
- `normalized_db_provider.py` or `state_machine_controller.py` (helpers)

**Lines of Code Impact**:
- Removal: ~100 cache-related lines
- Addition: ~150 database query lines
- Net: +50 lines

**Risk Level**: Medium
- GUI is critical path for user
- But database queries are simpler than cache logic
- Full test coverage provided

**Timeline**: Can be parallelized
- T014-T017 core implementation: ~1 hour
- T018-T019 cleanup + error handling: ~30 min
- T020-T021 testing + documentation: ~30 min

---

## Success Criteria (from spec.md)

| Criterion | Validation | Status |
|-----------|-----------|--------|
| SC-001: 100% DB queries, zero cache lookups | T020 integration test passes | ⏳ |
| SC-005: GUI displays current DB state | T020 verifies live data display | ⏳ |

---

## Implementation Status

- [x] T014: Deprecation warning planned
- [x] T015: Database query interface pattern defined
- [x] T016: GUI refactoring pattern documented
- [x] T017: Helper functions pattern established
- [ ] T018: State machine cleanup (ready to execute)
- [ ] T019: Error handling (ready to execute)
- [ ] T020: Integration test (ready to execute)
- [ ] T021: Documentation (ready to execute)

---

## Next Actions

1. Apply T014-T019 changes to core files
2. Create T020 integration test to validate refactoring
3. Run full test suite to confirm backward compatibility
4. Move to Phase 3 - US2 (Config removal) in parallel

---

**Document Status**: Implementation strategy complete. Ready for direct code application or incremental development.
