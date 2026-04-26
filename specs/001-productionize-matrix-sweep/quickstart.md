# Quickstart: Verify Matrix Sweep Productionization

## Assumptions

- Work from `C:\Users\U446541\sandbox\riverghost`
- Use the existing virtual environment and current HoPilot Python/SQLAlchemy/Pygame stack
- Run tests against temporary SQLite databases, not the production database file

## Verification Flow

1. Activate the project environment.
2. Run the matrix sweep raw-phase and aggregation tests to confirm GameStates-first persistence and 169-cell summary creation.
3. Run the pipeline and precompute-runner tests to confirm run-boundary isolation, append-only history, and production routing through `MatrixSweepService`.
4. Run the architecture boundary test to confirm production code does not import from `prototyping/`.

## Verification Command

```powershell
.venv\Scripts\Activate.ps1
python -m pytest tests/test_matrix_sweep_service.py tests/test_matrix_sweep_aggregation_service.py tests/test_matrix_sweep_pipeline.py tests/test_matrix_sweep_precompute_runner.py tests/integration/test_architecture_boundaries.py -q
```

## Expected Assertions

- raw sweep writes `GameState` and `Player` rows only
- no `HandMatrix`, `MatrixCell`, or `AggregatedMetric` rows exist before aggregation
- completed run contains exactly one `Simulation` and one `HandMatrix`
- completed run contains exactly 169 `MatrixCell` and 169 `AggregatedMetric` rows
- aggregation rerun recreates only the selected run's summaries and leaves raw rows intact
- new runs append new `Simulation` and `HandMatrix` records without mutating prior run summaries
- precompute execution goes through `MatrixSweepService`
- production code remains free of `prototyping/` imports

## Recorded Verification Evidence

- 2026-04-26: `python -m pytest tests/test_matrix_sweep_service.py tests/test_matrix_sweep_aggregation_service.py tests/test_matrix_sweep_pipeline.py tests/test_matrix_sweep_precompute_runner.py tests/integration/test_architecture_boundaries.py -q`
- Result: `10 passed in 51.66s`

## Manual Inspection Targets

- `Simulation.parameters` contains the canonical scenario contract, raw boundary metadata, `matrix_id`, and final `status`
- hero `Player.hole_cards` values map back to canonical cell coordinates during aggregation
- no production matrix sweep path depends on `GameState.cell_id` or `board_cards_id`