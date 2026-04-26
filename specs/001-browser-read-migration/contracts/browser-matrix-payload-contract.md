# Contract: Browser Matrix Payload

## Interface Type

Internal provider contract consumed by GUI components through `BrowserDatabaseProvider.get_matrix_payload(...)`.

## Operation

`get_matrix_payload(position, metric, position_actions=None, pot_size=20.0, bet_amount=10.0, strict_current_action=False, allow_compute=True, on_cell_complete=None) -> payload`

## Request Contract

### Required inputs

- `position`: browser-selected seat
- `metric`: browser-selected metric ID

### Optional inputs

- `position_actions`: browser action map
- `pot_size`
- `bet_amount`
- `strict_current_action`: deprecated, ignored for scenario matching
- `allow_compute`: retained for compatibility, must not trigger writes in this feature
- `on_cell_complete`: compatibility callback for payload formatting flow

## Response Contract

### Success payload (matching run)

- `context`: normalized browser context
- `cells`: 169 canonical cells
- `status`: `AVAILABLE`
- `status_message`: provider-defined success message

Success rules:

- the provider first attempts the aggregation-backed read path for the canonical scenario contract
- browser metric switching changes only which aggregated value is read from the selected run
- invalid-context validation and `NO_CONTEST` short-circuit handling remain provider-owned compatibility behavior

Each cell includes:

- `row`
- `col`
- `hand_key`
- `value`
- `status`
- `display`

### Missing payload (no matching run or no aggregated matrix)

- `context`: normalized browser context
- `cells`: 169 canonical cells
- `status`: `MISSING`
- `status_message`: explicit missing-data message

Cell rules:

- preserve `row`, `col`, and `hand_key`
- `value = null`
- no `LOADING` or `Computing...`
- no implicit background compute or persistence side effect

### Invalid-context payload

- preserves current provider compatibility behavior
- `cells` may remain empty
- `status = MISSING`
- `status_message` explains validation failure

### No-contest payload

- preserves current provider-owned compatibility behavior
- provider synthesizes 169 available cells without repository selection
- `status = AVAILABLE`

## Behavioral Guarantees

- provider remains responsible for context construction and GUI payload formatting
- repository or read service owns scenario lookup and current-run selection
- browser metric switching changes only the selected value field, not the scenario contract
- read path is strictly read-only
- unmatched scenarios use the explicit missing payload instead of the legacy loading fallback