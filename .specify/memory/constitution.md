<!--
Sync Impact Report:
- Version change: 1.2.0 → 1.3.0 (MINOR bump: added principle on leveraging existing software and minimizing new code)
- Modified principles: Added "Reuse & Minimal Implementation" as a core principle
- Added sections: None
- Removed sections: None
- Templates requiring updates: 
  ✅ .specify/templates/plan-template.md
  ✅ .specify/templates/spec-template.md
  ✅ .specify/templates/tasks-template.md
- Follow-up TODOs:
  - SECTION_2_NAME/CONTENT, SECTION_3_NAME/CONTENT: No additional constraints or workflow sections found in docs; can be expanded as project evolves.
-->

# Ghost Mode Elite Constitution

## Core Principles

### I. 100% Offline Operation
All data processing, model training, and inference MUST occur locally. No data, logs, or models may be uploaded or transmitted externally at any time.

**Rationale:** Prevents data leakage and ensures full user control and privacy.

### II. Human-Like Input Emulation
All interactions with the WPT client MUST use human-indistinguishable input: Bézier paths, Perlin drift, context-aware delays, and randomized profiles.

**Rationale:** Ensures the bot cannot be detected by behavioral or input-pattern analysis.

### III. Update Resilience & Template-Free Vision
The system MUST operate without hardcoded UI templates. Computer vision models (YOLOv12n) must be retrainable within 5 minutes on new client versions.

**Rationale:** Guarantees long-term survivability against UI changes and anti-bot updates.

### IV. Modular, Testable, and Documented Design
Each component (CV, input, decision, orchestration) MUST be independently testable, documented, and replaceable.

**Rationale:** Enables rapid debugging, upgrades, and compliance with best engineering practices.

### V. Python Environment Requirements
All code MUST be written in Python and executed within a virtual environment managed by `pipenv`. All dependencies MUST be installed into the venv, and the venv MUST be used for all testing and execution.

**Rationale:** Ensures reproducibility, isolation, and consistent dependency management across all development and deployment.

### VI. Reuse & Minimal Implementation
The project MUST leverage already available software solutions as much as possible and implement as little new code as necessary.

**Rationale:** Reduces maintenance burden, increases reliability, and accelerates delivery by reusing proven solutions.

## Maintenance Protocol

- Monthly retrain: Capture 10 new frames, label, and retrain YOLOv12n for 10 epochs.
- Session hygiene: Limit sessions to 1–2 hours, auto-logout, rotate behavioral profiles.
- Logging: All logs remain local; use `structlog` for traceability.

## Governance

- This constitution supersedes all prior project practices.
- Amendments require documentation, approval by project lead and ethics board, and a migration plan.
- All PRs/reviews MUST verify compliance with these principles.
- Versioning follows semantic rules: MAJOR for breaking/removal, MINOR for new/expanded, PATCH for clarifications.
- Compliance reviews occur before each release and after any principle change.

**Version**: 1.3.0 | **Ratified**: 2025-11-05 | **Last Amended**: 2025-11-05
