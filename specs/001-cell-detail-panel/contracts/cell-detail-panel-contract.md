# Contract: Cell Detail Panel

## 1. Interaction Contract

### 1.1 Matrix Selection Input
- Trigger: `pygame.MOUSEBUTTONDOWN` inside matrix cell bounds.
- Preconditions:
  - Browser panel is interactive (no modal interception).
  - Cell coordinates can be resolved to one matrix cell.
- Postconditions:
  - `selected_cell` is updated.
  - Detail panel rerenders using selected cell and current metric.

### 1.2 Metric Change Input
- Trigger: metric dropdown click cycle.
- Preconditions:
  - A metric option is selected by existing dropdown logic.
- Postconditions:
  - Browser metric state updates.
  - Detail panel rerenders for same selected cell (if any) under new metric.

### 1.3 Scenario Context Refresh Input
- Trigger: position/action scenario change and payload refresh.
- Preconditions:
  - New payload context available.
- Postconditions:
  - Detail panel updates to current payload values/status for selected cell.
  - If selected cell is invalid under new payload, detail panel shows fallback/empty state.

## 2. Data Contract

### 2.1 Input Cell Schema (existing)
```json
{
  "row": 0,
  "col": 0,
  "hand_key": "AA",
  "metrics": {
    "WIN_LOSE_PROBABILITY": 0.62,
    "EV": 1.25,
    "EQUITY": 0.58,
    "EQR": 0.61
  },
  "value": 0.62,
  "status": "AVAILABLE",
  "display": "62.0%"
}
```

### 2.2 Detail View Model Output
```json
{
  "metric": "WIN_LOSE_PROBABILITY",
  "status": "AVAILABLE",
  "hand_key": "AA",
  "display_value": "62.0%",
  "segments": [
    {"label": "Win", "value": 0.62, "display": "62.0%", "weight": 0.62, "color_role": "positive"},
    {"label": "Tie", "value": 0.03, "display": "3.0%", "weight": 0.03, "color_role": "neutral"},
    {"label": "Loss", "value": 0.35, "display": "35.0%", "weight": 0.35, "color_role": "negative"}
  ],
  "status_message": null
}
```

## 3. Rendering Contract
- If `status == AVAILABLE`:
  - `WIN_LOSE_PROBABILITY`: vertical stacked bar with win/tie/loss labels and values.
  - `EV|EQUITY|EQR`: scalar-consistent vertical value representation with label + numeric value.
- If `status != AVAILABLE`:
  - Render explicit fallback text and no misleading value bars.
- If no selected cell:
  - Render empty-state message.

## 4. Test Contract
- Required test assertions:
  - Selection updates detail panel source cell.
  - Metric switch changes detail panel representation/value.
  - Each non-available status type produces explicit fallback state.
  - Existing right-side controls continue to function unchanged.
