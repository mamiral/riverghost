# riverghost Development Guidelines

Repository-specific guardrails for agent execution.

## Python Environment (MANDATORY)
- Always use the project virtual environment at `.venv`.
- In terminal sessions, activate first when running multiple commands:

```powershell
.\.venv\Scripts\Activate.ps1
```

- For single-command execution, using the fully qualified interpreter is equivalent and preferred for reliability:

```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest ...
```

- Do not run `python`, `pip`, or `pytest` from global/system PATH for project work.

## Project Structure

```text
python/
	hopilot/
tests/                    # ← Test files go HERE (root level)
config/
specs/
```

**CRITICAL**: Test files must be in root `tests/` directory, NOT `python/tests/`

## Commands
- Run tests from repository root:

```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests -q
```

- Run specific test file:

```powershell
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m pytest tests/test_file.py
```

- Run app modules from `python/` directory:

```powershell
cd python
c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe -m hopilot.aof_gto_browser_gui
```

## Active Technologies
- Python 3.13 (project virtual environment)
- pygame, pytest, pydantic, yaml
- SQLAlchemy + SQLite (offline AoF cache feature)
- Existing hopilot modules (`all_in_fold_gto`, `aof_solver_adapter`, `aof_browser_data_provider`)
- Python 3.13 (project virtual environment) + pygame UI components, existing AoF modules (`aof_browser_panel`, `aof_browser_data_provider`, `aof_precompute_runner`, `aof_scenario_cache_store`), SQLAlchemy-backed cache models (001-gui-precompute-runner)
- Existing SQLite cache store (`python/hopilot/cache/aof_scenario_cache.sqlite3`) with run/checkpoint metadata in precompute tables (001-gui-precompute-runner)
- Python 3.13 (project venv runtime) + `pygame`, existing HoPilot AoF GUI/payload modules (001-cell-detail-panel)
- N/A (read-only UI over existing in-memory payload) (001-cell-detail-panel)
- Python 3.11 + pygame, sqlalchemy, pydantic, treys, numpy (001-aggregated-aof-stats)
- SQLite with SQLAlchemy ORM (001-aggregated-aof-stats)
- Python 3.x (existing project standard) + SQLAlchemy (ORM for database abstraction), SQLite (built-in Python support) (001-normalized-db-schema)
- SQLite database file with SQLAlchemy ORM abstraction for future PostgreSQL migration (001-normalized-db-schema)
- Python 3.x (existing project standard) + SQLAlchemy (ORM for database abstraction), SQLite (built-in Python support), existing browser components (AoFBrowserDataProvider, AoFBrowserPanel) (001-db-schema-browser-integration)
- SQLite database with normalized relational schema (9 tables: Simulations, HandMatrices, MatrixCells, GameStates, Players, Bets, BoardCards, Jackpots, AggregatedMetrics) (001-db-schema-browser-integration)
- [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION] + [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION] (001-gui-state-refactor)
- [if applicable, e.g., PostgreSQL, CoreData, files or N/A] (001-gui-state-refactor)
- Python 3.x (confirmed: virtual environment with .venv, requirements.txt dependencies) (003-state-machine-completion)
- Python 3.11+ + SQLAlchemy ORM (existing), Pydantic (config validation), pytest (testing) (001-cache-removal)
- SQLAlchemy-managed normalized database (PostgreSQL, SQLite, or configured backend) (001-cache-removal)
- Python 3.x + pytest, unittest.mock (001-test-suite-cleanup)
- SQLite databases (for test data persistence) (001-test-suite-cleanup)

## Operational Notes
- Keep standalone AoF browser decoupled from simulator flow.
- Preserve deterministic status semantics (`AVAILABLE`, `MISSING`, `NO_CONTEST`, `TIMEOUT`, `ERROR`).
- Cache and precompute features should include structured logging and pytest coverage.
