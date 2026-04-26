# Quickstart: Verify Browser Read-Path Migration

## Assumptions

- Work from `C:\Users\U446541\sandbox\riverghost`
- Use the existing project virtual environment
- Run tests against temporary SQLite databases or isolated test fixtures, not the production database file

## Verification Flow

1. Activate the project environment.
2. Run the browser provider unit and persistence tests covering invalid context, `NO_CONTEST`, missing scenario, and metric mapping behavior.
3. Run the browser integration tests covering real run selection and missing-run responses.
4. Run the matrix sweep pipeline test that proves the provider can resolve a persisted scenario contract to the correct run summary.

## Verification Command

```powershell
.venv\Scripts\Activate.ps1
python -m pytest tests/test_browser_database_provider.py tests/test_browser_database_provider_persistence.py tests/integration/test_browser_database_provider_integration.py tests/test_matrix_sweep_pipeline.py -q
```

## Expected Assertions

- invalid browser context returns the existing validation payload without raising
- `NO_CONTEST` scenarios still return provider-generated available payloads
- a matching aggregated scenario returns exactly 169 canonical cells from one selected run
- repeated reads for the same scenario select the same current historical run
- a missing scenario returns explicit missing status, not `LOADING`
- a matching run without a `HandMatrix` is treated as missing
- cells with missing metric data substitute `0`
- browser reads do not create new `Simulation`, `HandMatrix`, `MatrixCell`, or `AggregatedMetric` rows

## Verified Result

- `python -m pytest tests/test_browser_database_provider.py tests/test_browser_database_provider_persistence.py tests/integration/test_browser_database_provider_integration.py tests/test_matrix_sweep_pipeline.py -q`
- result: `40 passed`

## Manual Inspection Targets

- `Simulation.parameters` stores the canonical contract fields used for lookup
- selected browser payload values come from the chosen run's `HandMatrix` only
- payload cell identity uses canonical `hand_key`, `row`, and `col`
- missing scenarios show explicit missing messaging without background-compute text