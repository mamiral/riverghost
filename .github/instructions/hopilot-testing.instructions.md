---
description: "Use when writing tests for HoPilot or ensuring code quality. Covers testing standards, forbidden behaviors, and validation patterns."
applyTo: "tests/**"
---

# HoPilot Testing Standards

## Strictly Forbidden Behaviour
- Never use fake data or take any other form of shortcut
- Always implement complete, working solutions
- Never write tests that check mocks instead of real implementation behavior
- Never use meaningless assertions like `assert True` or only check basic object existence
- Never expect deterministic results from random or non-deterministic behavior
- Never write placeholder tests with `pass` or incomplete logic
- Always ensure tests validate actual functionality and correctness, not just that methods can be called

## Testing Setup
- Run tests from project root (`C:\Users\U446541\sandbox\riverghost`): `pytest` (configured in `pytest.ini`)
- Test files in `tests/` directory (NOT `python/tests/`)
- pytest.ini configures `testpaths = tests` for proper discovery
- Add `sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))` in test files to access hopilot module

## Running Tests
```bash
pytest tests/test_poker_analyzer.py -v
pytest tests/ -k "card"  # Run card-related tests
```

## Test Principles
- Every test should validate real behavior, not mocks
- Deterministic tests only—never test inherently random behavior directly
- For Monte Carlo simulations: test convergence and statistical properties, not exact values
- Use fixtures for common setup (config, test data, temporary files)
- Name tests descriptively: `test_<function>_<condition>_<expected_outcome>`
