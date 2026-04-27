# Contract: Replay Read

## Purpose

Define the supported request and response behavior for replaying one stored hand from the current raw schema.

## Request

### ReplayReadRequest

```text
game_state_id: integer >= 1
include_optional_details: boolean (default true)
```

## Resolution Rules

1. Load one `GameState` by `game_state_id`.
2. Load related `Player` rows.
3. Optionally load related `Bet` and `Jackpot` rows if the caller asked for optional details.
4. Parse board cards from `GameState.board_cards_str`.
5. Do not consult `GameState.cell_id`, `matrix_id`, `BoardCard`, or matrix-cell relationships.

## Response

### ReplayView

```text
game_state_id: integer
timestamp: string | null
round: string
pot_size: number
outcome: string | null
board_cards: list[string]
players: list[ReplayPlayerView]
optional_details:
  bets: list[object]
  jackpots: list[object]
  availability: map[string, string]
replay_status: READABLE | UNREADABLE | NOT_FOUND
status_message: string | null
```

### ReplayPlayerView

```text
position: string
hole_cards: string
is_hero: boolean
hand_class: string | null
final_strength: integer | null
stack_size: number
```

## Readability Rules

- `READABLE`: the game state exists and has enough persisted player data to produce a truthful replay.
- `UNREADABLE`: the game state exists but required player rows are missing or inconsistent.
- `NOT_FOUND`: the game state does not exist.

## Status Semantics

- `READABLE` MUST include at least one persisted player row and MUST return `players` populated from persisted `Player` records.
- `UNREADABLE` MUST return an explanatory `status_message` and MUST NOT fabricate missing player, board, bet, or jackpot data.
- `NOT_FOUND` MUST return no replay body for an unknown `game_state_id` beyond status metadata.
- `optional_details.availability` MUST include both `bets` and `jackpots` keys with values in `available | unavailable`.
- `optional_details.bets` and `optional_details.jackpots` MUST be empty lists when unavailable, never omitted.

## Truthfulness Rules

- `board_cards` comes only from `board_cards_str`.
- empty or null `board_cards_str` yields an empty board-card list.
- optional `Bet` and `Jackpot` details are included only when persisted rows exist.
- the contract must never invent action sequences, street reveals, or jackpot history.

## Example Outcomes

### Readable Preflop Hand

```text
replay_status: READABLE
board_cards: []
players: [hero row, villain rows...]
optional_details.availability.bets: unavailable
```

### Stored Hand Missing Players

```text
replay_status: UNREADABLE
status_message: stored hand is missing required player rows
players: []
```