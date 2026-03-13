# Data Model: Standalone AoF GTO Solution Browser

## Entity: PositionContext
- Purpose: Defines currently selected player perspective for strategy lookup.
- Fields:
  - id: enum {UTG, BTN, SB, BB}
  - label: string
  - sort_order: integer
- Validation rules:
  - Must be one of exactly four supported values.
- Relationships:
  - One PositionContext maps to many StrategyCellMetricValue rows via action and metric filters.

## Entity: ActionContext
- Purpose: Defines selected decision branch to display in the matrix.
- Fields:
  - id: enum {FOLD, ALL_IN}
  - label: string
- Validation rules:
  - Must be one of two supported values.
- Relationships:
  - Combined with PositionContext and MetricType to select matrix payload.

## Entity: MetricType
- Purpose: Defines the meaning and formatting rules for matrix values.
- Fields:
  - id: enum {WIN_LOSE_PROBABILITY, EV, EQUITY, EQR}
  - label: string
  - display_format: enum {percent, decimal, signed_decimal}
- Validation rules:
  - Must be one of the four spec-required options.

## Entity: HandKey
- Purpose: Canonical identifier for a matrix hand cell.
- Fields:
  - key: string (examples: AA, AKs, AKo, 72o)
  - row_rank: enum {A,K,Q,J,T,9,8,7,6,5,4,3,2}
  - col_rank: enum {A,K,Q,J,T,9,8,7,6,5,4,3,2}
  - suitedness: enum {PAIR, SUITED, OFFSUIT}
- Validation rules:
  - Exactly 169 unique keys must exist in matrix topology.
  - Pair keys must use identical ranks and suitedness=PAIR.
  - Non-pair keys must resolve to either SUITED or OFFSUIT.

## Entity: StrategyCellMetricValue
- Purpose: Stores displayable value and status for one hand under a specific context.
- Fields:
  - position: PositionContext.id
  - action: ActionContext.id
  - metric: MetricType.id
  - hand_key: HandKey.key
  - value: float | null
  - status: enum {AVAILABLE, MISSING, INVALID}
  - source_tag: string | null
  - updated_at: datetime
- Validation rules:
  - Composite uniqueness: (position, action, metric, hand_key).
  - If status=AVAILABLE, value must be non-null and finite.
  - If status in {MISSING, INVALID}, value must be null.

## Entity: AoFBrowserViewState
- Purpose: In-memory UI state controlling matrix rendering.
- Fields:
  - selected_position: PositionContext.id
  - selected_action: ActionContext.id
  - selected_metric: MetricType.id
  - hover_hand: HandKey.key | null
  - status_message: string | null
- State transitions:
  - On app launch: initialize to defaults (position/action/metric) and render initial matrix.
  - On position change: update selected_position and refresh matrix payload.
  - On action change: update selected_action and refresh matrix payload.
  - On metric change: update selected_metric and refresh matrix payload.
  - On missing dataset context: keep state selections, set status_message, render missing cell states.
