# Contract: AoF GTO Browser UI Interaction Contract

## Purpose
Defines externally observable behavior for the standalone AoF GTO Solution Browser UI so tests and downstream integrations can validate expected interactions.

## UI Surface Contract

### 1. Position Selector
- Exposes exactly four selectable controls in this semantic set:
  - UTG
  - BTN
  - SB
  - BB
- Contract rules:
  - Exactly one position is active at a time.
  - Selecting a new position emits a state-change event: `position.changed`.

### 2. Action Selector
- Exposes two selectable action controls:
  - FOLD
  - ALL_IN
- Contract rules:
  - Exactly one action is active at a time.
  - Selecting a new action emits: `action.changed`.

### 3. Metric Dropdown
- Exposes these options exactly:
  - WIN_LOSE_PROBABILITY
  - EV
  - EQUITY
  - EQR
- Contract rules:
  - Exactly one metric is active at a time.
  - Selecting a new metric emits: `metric.changed`.

### 4. Hand Matrix
- Exposes a fixed 13x13 grid representing all pair/suited/offsuit preflop hand categories.
- Contract rules:
  - Matrix must redraw when any of position/action/metric changes.
  - Each cell must represent one canonical hand key.
  - Missing or invalid data must render as non-stale placeholder state.

## Event-to-Render Contract
For each UI event `position.changed`, `action.changed`, or `metric.changed`:
1. Browser updates its canonical view state.
2. Browser requests matrix values using tuple `(position, action, metric)`.
3. Browser redraws matrix from returned dataset.
4. Browser updates active-control highlighting and status message area.

## Data Payload Contract (View Layer)
Input payload consumed by matrix renderer:
- context:
  - position: string enum {UTG, BTN, SB, BB}
  - action: string enum {FOLD, ALL_IN}
  - metric: string enum {WIN_LOSE_PROBABILITY, EV, EQUITY, EQR}
- cells: list of 169 entries
  - hand_key: string
  - value: number | null
  - status: string enum {AVAILABLE, MISSING, INVALID}

## Error and Empty-State Contract
- If payload for selected context is unavailable:
  - Browser shows informative, non-blocking status message.
  - Browser does not display stale values from prior context.
  - User may continue switching position/action/metric controls.

## Non-Goals
- No contract for running new solves in this UI.
- No contract for network APIs; data source remains internal to HoPilot modules for this feature.
