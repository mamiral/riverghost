---
description: "Use when working with HoPilot configuration: loading, accessing game modes, slots, and seat configurations. Covers config structure and immutability patterns."
---

# HoPilot Configuration Patterns

## Loading Configuration
- Load config via: `config = load_config("config.yaml")`
- Default config available as: `DEFAULT_CONFIG`
- Load once at startup—don't reload during runtime
- Store reference in module-level variable or pass as dependency

## Configuration Structure
- Top level: `game_modes` (dict of game configurations)
- Game mode: `game_modes["rush_n_cash"]` (specific game)
- Seats: `game_modes["rush_n_cash"].slots` (all seat positions)
- Seat: `game_modes["rush_n_cash"].slots["hero_hole_1"]` (specific seat)

## Access Patterns
```python
# Load once
config = load_config("config.yaml")

# Access game mode
mode = config.game_modes["rush_n_cash"]

# Access seat configuration
hero_seat = mode.slots["hero_hole_1"]

# Access seat properties
position = hero_seat.position
role = hero_seat.role
```

## Immutability
- Configuration is immutable after loading
- Never modify config at runtime—create a new config object if changes needed
- If dynamic configuration needed, validate pattern first

## Configuration Validation
- Pydantic validates config structure on load
- Invalid YAML or missing fields raise errors during `load_config()`
- Handle configuration errors at application startup, not mid-analysis

## Common Slots
- Hole cards: `"hero_hole_1"`, `"hero_hole_2"`, `"opponent_hole_1"`, `"opponent_hole_2"`
- Board: `"flop_1"`, `"flop_2"`, `"flop_3"`, `"turn"`, `"river"`
- Reference config.yaml for complete seat list
