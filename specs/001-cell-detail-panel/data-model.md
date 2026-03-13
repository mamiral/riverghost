# Data Model: Cell Detail Middle Panel

## Entity: CellSelectionState
- Purpose: Represents the user-selected matrix cell that drives the middle detail panel.
- Fields:
  - `row` (int, 0-12)
  - `col` (int, 0-12)
  - `hand_key` (str, non-empty)
  - `selected_at` (optional float timestamp for debugging/telemetry, non-persistent)
- Validation Rules:
  - `row` and `col` must be within matrix bounds.
  - `hand_key` must match payload cell `hand_key` at `(row, col)`.
- State Transitions:
  - `None -> Selected`: user clicks valid matrix cell.
  - `Selected(A) -> Selected(B)`: user clicks another valid cell.
  - `Selected -> None`: optional explicit clear action or payload invalidation case.

## Entity: CellDetailViewModel
- Purpose: Normalized display model consumed by the middle detail panel renderer.
- Fields:
  - `metric` (enum string: `WIN_LOSE_PROBABILITY|EV|EQUITY|EQR`)
  - `status` (enum string: `AVAILABLE|MISSING|TIMEOUT|ERROR|NO_CONTEST`)
  - `primary_value` (float | None)
  - `segments` (list of `MetricSegment`)
  - `display_value` (str)
  - `status_message` (str | None)
  - `hand_key` (str)
- Validation Rules:
  - If `status != AVAILABLE`, `segments` may be empty and `status_message` must be set.
  - If `metric == WIN_LOSE_PROBABILITY` and `status == AVAILABLE`, segments include win/tie/loss.
  - If scalar metric (`EV|EQUITY|EQR`) and `status == AVAILABLE`, include one semantic segment/value indicator.

## Entity: MetricSegment
- Purpose: One visual segment/value definition inside detail panel.
- Fields:
  - `label` (str; examples: `Win`, `Tie`, `Loss`, `Value`)
  - `value` (float)
  - `display` (str formatted for UI)
  - `color_role` (str token mapped to panel palette)
  - `weight` (float >= 0, used for proportional vertical sizing)
- Validation Rules:
  - `weight` must be non-negative.
  - For WIN_LOSE_PROBABILITY available state, sum of segment weights should be approximately 1.0.

## Relationships
- `CellSelectionState` identifies one source payload cell.
- Selected payload cell + current metric + current status map to one `CellDetailViewModel`.
- `CellDetailViewModel` contains 1..N `MetricSegment` entries depending on metric/status.

## Derivation Rules
- Source data comes from existing matrix payload cell schema (`row`, `col`, `hand_key`, `metrics`, `value`, `status`, `display`).
- WIN_LOSE_PROBABILITY detail model should derive win/tie/loss components from available metric bundle/context.
- EV/EQUITY/EQR detail model derives scalar display from `value`/`metrics` and standardized formatting.

## Failure/Fallback Mapping
- `MISSING`: show "No cached value for this cell" fallback.
- `TIMEOUT`: show timeout fallback with neutral styling.
- `ERROR`: show computation/error fallback with error styling.
- `NO_CONTEST`: show no-contest fallback indicating scenario not contested.
