# Data Model: Solver-Backed AoF Browser

## BrowserContext
- Description: Input context for matrix computation.
- Fields:
  - `selected_position`: enum (`UTG`, `BTN`, `SB`, `BB`)
  - `position_actions`: map of position -> enum (`FOLD`, `ALL_IN`)
  - `metric`: enum (`WIN_LOSE_PROBABILITY`, `EV`, `EQUITY`, `EQR`)
  - `pot_size`: positive float
  - `bet_amount`: positive float
  - `num_simulations`: bounded integer
  - `timeout_ms`: positive integer
- Validation rules:
  - All positions must be present in `position_actions`.
  - Only supported enum values allowed.
  - Numeric fields must be positive and within configured bounds.

## SolverEvaluationRecord
- Description: Intermediate combo-level evaluation used for cell aggregation.
- Fields:
  - `hand_key`: string (`AA`, `AKs`, `KQo`, ...)
  - `combo`: tuple of 2 cards
  - `win_probability`: float [0, 1]
  - `loss_probability`: float [0, 1]
  - `equity`: float [0, 1]
  - `ev`: float
  - `eqr`: float [0, 1] or defined normalized ratio
  - `is_valid`: boolean
  - `invalid_reason`: optional enum/text

## MatrixCellResult
- Description: Aggregated per-hand output consumed by UI matrix.
- Fields:
  - `row`: integer [0, 12]
  - `col`: integer [0, 12]
  - `hand_key`: string
  - `value`: nullable float
  - `display`: string
  - `status`: enum (`AVAILABLE`, `MISSING`, `NO_CONTEST`, `TIMEOUT`, `ERROR`)
- Validation rules:
  - `value` must be null when status is non-available.
  - In probability mode, if `value` exists it represents win probability and loss is derived as `1 - value`.

## MatrixPayload
- Description: Full provider response used by browser panel.
- Fields:
  - `context`: object snapshot of `BrowserContext` plus derived fields (`active_players`, effective mode)
  - `cells`: list of 169 `MatrixCellResult`
  - `status_message`: optional user-facing status

## EdgeCaseResolution
- Description: Deterministic mapping from exceptional context to payload behavior.
- Fields:
  - `edge_case_key`: enum (`ALL_FOLD`, `SINGLE_ALL_IN`, `SELECTED_FOLD`, `UNCONTESTED_WIN`, `MULTIWAY_ALL_IN`, `NO_VALID_COMBOS`, `SOLVER_TIMEOUT`, `SOLVER_FAILURE`, `UNSUPPORTED_CONTEXT`)
  - `cell_status`: status enum used in payload
  - `value_semantics`: brief policy text
  - `ui_message`: deterministic status message

## CacheEntry
- Description: Stored payload and metadata for repeated contexts.
- Fields:
  - `cache_key`: stable hash of context + parameters
  - `payload`: `MatrixPayload`
  - `created_at`: timestamp
  - `expires_at`: optional timestamp
  - `solver_signature`: version marker for invalidation
- Invalidation triggers:
  - Any context field change.
  - Solver or metric computation rule version change.
  - Explicit timeout/failure stale-entry policy.
