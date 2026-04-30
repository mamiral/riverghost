# Quickstart: Database Repository Refactor Validation

## Purpose
Validate the staged repository refactor while preserving existing behavior.

## 1) Environment
- Use project venv on Windows PowerShell.
- Run commands from repository root.

```powershell
.venv\Scripts\Activate.ps1
```

## 2) Migration Step Validation (Targeted Suites)
Run targeted suites relevant to the current migration step.

```powershell
pytest tests/test_database_repository.py tests/test_database_repository_writes.py -q
pytest tests/test_precompute_job_persistence.py tests/test_precompute_runner_regression.py -q
pytest tests/integration/test_precompute_runner_integration.py tests/integration/test_browser_database_provider_integration.py -q
pytest tests/contract/test_precompute_runner_contracts.py tests/contract/test_provider_contract_split.py -q
```

## 2.1) Foundational Phase Validation
After Phase 1 and 2 work, validate shared infrastructure with:

```powershell
pytest tests/test_repository_unit_of_work.py tests/test_repository_validation.py -q
```

## 2.2) US3 Isolation and Diagnostics Validation
After domain-boundary hardening, validate failure isolation and diagnostics attribution:

```powershell
pytest tests/test_repository_unit_of_work.py tests/test_repository_validation.py tests/test_repository_failure_isolation.py tests/test_repository_transaction_atomicity.py tests/test_repository_diagnostics.py -q
```

## 3) Full Regression Gate (Before Merge)

```powershell
pytest tests/
```

## 4) Consumer Migration Trigger Check
Confirm both trigger consumers are migrated before facade removal:
- `python/hopilot/gto/aof_precompute_runner.py`
- `python/hopilot/gto/precompute_job_persistence.py`

Current implementation status:
- Trigger consumers are migrated to split repositories.
- `DatabaseRepository` remains as a compatibility facade for legacy/runtime and test call sites; domain ownership is implemented in split repositories.

## 5) Behavioral Checks
- Precompute job/session tracking lifecycle remains unchanged.
- Raw game-state write semantics remain unchanged.
- Browser matrix/query behavior remains unchanged.

## 6) Completion Conditions
- Targeted suites pass per migration step.
- Full suite passes before merge.
- Split repositories own behavior; compatibility facade remains thin and delegating.
