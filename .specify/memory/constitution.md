<!--
Sync Impact Report:
- Version change: 2.1.0 → 2.2.0 (MINOR bump: added Established Design Patterns principle)
- Modified principles: None
- Added sections: XI. Established Design Patterns
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

## Additional Requirements
All code must run from the python/ directory with relative imports. Use venv for environment management. Comprehensive testing with pytest. Consistent logging via centralized config.

## Development Workflow
Run commands from python/ directory. Use venv for dependencies. Test with pytest. Document in plans/ and docs/.

## Governance
This constitution supersedes all prior project practices. Amendments require documentation and approval. All changes must comply with principles. Versioning follows semantic rules: MAJOR for breaking/removal, MINOR for new/expanded, PATCH for clarifications.

**Version**: 2.2.0 | **Ratified**: 2025-11-05 | **Last Amended**: 2026-03-15
