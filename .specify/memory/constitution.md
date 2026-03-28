<!--
Sync Impact Report:
- Version change: 2.2.1 → 2.3.0 (MINOR bump: added Quality Assurance principle)
- Modified principles: None
- Added sections: XII. Quality Assurance under Core Principles
- Removed sections: None
- Templates requiring updates: None
- Follow-up TODOs: None
-->

# HoPilot Constitution

## Core Principles

### I. Real-Time Poker Analysis
The tool MUST provide real-time poker odds calculation using Monte Carlo simulations based on detected cards.

**Rationale:** To enable informed decision-making during live poker games.

### II. Computer Vision Accuracy
Card detection MUST use computer vision techniques to accurately identify cards from game screenshots.

**Rationale:** Accurate card recognition is essential for reliable analysis.

### III. Modular Design
The system MUST consist of modular, independently testable components for card detection, analysis, and GUI.

**Rationale:** Facilitates maintenance, testing, and extension.

### IV. Configuration Management
Configuration MUST be handled through validated YAML files using Pydantic.

**Rationale:** Ensures configuration integrity and ease of setup.

### V. Real-Time Screen Capture
Real-time screen capture MUST be supported using platform-specific libraries.

**Rationale:** Enables live analysis of poker games.

### VI. Comprehensive Testing
All components MUST be thoroughly tested using pytest, with mocking of external dependencies.

**Rationale:** Ensures code quality and reliability.

### VII. Consistent Logging
Logging MUST be implemented consistently using a centralized logging configuration.

**Rationale:** Aids in debugging and monitoring the application.

### VIII. Virtual Environment Management
All Python code MUST run within a virtual environment managed by venv or similar tools.

**Rationale:** Ensures dependency isolation and reproducibility.

### IX. DRY Principle (Don't Repeat Yourself)
Code MUST not contain duplication. Common functionality MUST be extracted into reusable functions, classes, or modules.

**Rationale:** Reduces maintenance burden and prevents inconsistencies.

### X. Single Responsibility Principle
Each class, function, and module MUST have a single, well-defined responsibility.

**Rationale:** Improves code maintainability, testability, and understandability.

### XI. Established Design Patterns
Code MUST use established software design patterns instead of inventing custom solutions for problems that have been solved countless times before.

**Rationale:** Leverages proven solutions, improves code quality, and enhances maintainability.

### XII. Quality Assurance
Never use fake data or take any other form of shortcut. Always implement complete, working solutions. Never write tests that check mocks instead of real implementation behavior. Never use meaningless assertions like `assert True` or only check basic object existence. Never expect deterministic results from random or non-deterministic behavior. Never write placeholder tests with `pass` or incomplete logic. Always ensure tests validate actual functionality and correctness, not just that methods can be called.

**Rationale:** Ensures all code and tests are genuine, complete, and validate real behavior rather than artificial constructs.

## Additional Requirements
All code must run from the python/ directory with relative imports. Use venv for environment management. Comprehensive testing with pytest. Consistent logging via centralized config.

### Testing Directory Structure
- Test files MUST be placed in the root `tests/` directory
- pytest.ini in root configures `testpaths = tests` for proper test discovery
- Run tests with: `python -m pytest tests/test_file.py` (from project root)
- NEVER create test directories under `python/` - use the root `tests/` directory only

**Rationale:** Maintains consistent project structure and proper test discovery.

## Development Workflow
Run commands from python/ directory. Use venv for dependencies. Test with pytest. Document in plans/ and docs/.

## Governance
This constitution supersedes all prior project practices. Amendments require documentation and approval. All changes must comply with principles. Versioning follows semantic rules: MAJOR for breaking/removal, MINOR for new/expanded, PATCH for clarifications.

**Version**: 2.3.0 | **Ratified**: 2025-11-05 | **Last Amended**: 2026-03-29
