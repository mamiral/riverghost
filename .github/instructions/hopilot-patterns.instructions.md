---
description: "Use when implementing HoPilot features, working with cards, configuration, GUI components, or logging. Covers universal coding patterns and conventions."
applyTo: "python/hopilot/**"
---

# HoPilot Base Patterns

## Imports & Module Structure
- Run all Python commands from the `python/` directory (relative imports)
- Use `from hopilot.logging_config import get_logger` for consistent logging
- Import structure: `from hopilot.module import Class`
- Each module should initialize its logger: `logger = get_logger(__name__)`

## Logging
- Initialize once via `import hopilot.logging_config`
- Use `logger = get_logger(__name__)` in every module
- Log levels: DEBUG (detailed), INFO (normal), WARNING, ERROR
- Don't log sensitive data (card ranges, player info without context)

## Error Handling
- Propagate errors with context—include what operation failed and why
- Don't silently catch exceptions; log at WARNING or ERROR level before handling
- For card detection: log confidence scores and fallback decisions
- For simulations: log convergence metrics and anomalies
