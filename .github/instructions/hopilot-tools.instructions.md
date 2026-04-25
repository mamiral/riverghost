---
description: "Use when exploring the codebase, understanding architecture, analyzing change impact, or documenting decisions. Covers codebase-memory-mcp tools for graph-based code analysis and knowledge capture."
---

# HoPilot Codebase Tools (MCP)

The project is indexed as a knowledge graph: **7,729 nodes** with **16,667 edges** enabling powerful code analysis.

## Tool Reference

### `search_graph()` — Find Code by Pattern
**When to use:** Locate functions, classes, or implementations matching a pattern.

**Returns:** Qualified names, file paths, line numbers, relevance rank.

**Example queries:**
```
"monte carlo simulation" → Find all Monte Carlo implementations
"hand evaluation" → Locate hand strength calculations
"equity" → Search equity-related functions
```

**Best for:**
- Finding similar implementations before writing code
- Locating test coverage for a feature
- Understanding who implements a concept

### `get_architecture()` — Understand Component Relationships
**When to use:** Before designing a feature or refactoring. Gets system-wide view.

**Returns:** Node/edge statistics, component labels, relationship types.

**Example:**
```python
get_architecture(aspects=["services", "dependencies", "structure"])
```

**Tells you:**
- What components exist (Methods: 1,691, Classes: 292, Functions: 271)
- How they relate (CALLS, DEFINES, TESTS edges)
- Module structure and dependencies

**Best for:**
- Pre-design phase: "What modules do I need to touch?"
- Understanding data flow: "How does X get to Y?"

### `trace_path()` — Analyze Call Chains
**When to use:** Understand who calls what, or impact of changes.

**Modes:**
- `calls` (default): Direct caller/callee relationships
- `data_flow`: Value propagation with arguments
- `cross_service`: HTTP/async calls through Routes

**Example:**
```python
trace_path(
  function_name="_run_monte_carlo_simulation",
  mode="calls",
  depth=2
)
# Returns: Who calls _run_monte_carlo_simulation?
# Result: calculate_odds, calculate_odds_range, 
#         find_gto_threshold, run_simulation, etc.
```

**Best for:**
- Impact analysis before refactoring
- Understanding feature flow
- Debugging: "Why is this function called?"

### `detect_changes()` — Analyze Change Impact
**When to use:** Before major refactoring. Understand cascading effects.

**Example:**
```python
detect_changes(
  project="C-Users-U446541-sandbox-riverghost",
  since="HEAD~1",
  depth=2
)
```

**Returns:** Full impact graph of recent changes.

**Best for:**
- Pre-refactor: "What will break if I change X?"
- Post-merge: "Did this change affect other modules?"
- Risk assessment: "How many modules depend on this?"

### `manage_adr()` — Store Architectural Decisions
**When to use:** Document design choices, trade-offs, optimization decisions.

**Modes:**
- `get` - Retrieve existing ADRs
- `update` - Add or modify ADR
- `sections` - List available sections

**Example:**
```python
manage_adr(
  project="C-Users-U446541-sandbox-riverghost",
  mode="update",
  content="""
  ## Caching Strategy for Monte Carlo Results
  
  **Decision:** Use SQLite cache with composite key (hand, board, opp_count).
  **Trade-off:** 50MB disk vs. 200ms simulation time per hand.
  **Validation:** Convergence tests confirm cache is valid.
  """
)
```

**Best for:**
- Capturing optimization decisions
- Documenting why a choice was made (for future maintainers)
- Linking to related code

### `get_code_snippet()` — Read Implementation
**When to use:** Get actual source code for a function/class.

**Example:**
```python
get_code_snippet(
  qualified_name="PokerAnalyzer._run_monte_carlo_simulation",
  project="C-Users-U446541-sandbox-riverghost",
  include_neighbors=true  # Show related code
)
```

**Best for:**
- Understanding existing patterns before implementing
- Verifying how a function works

## Workflow Patterns

### Before Implementing a Feature
```
1. search_graph("your feature") → Find similar code
2. get_code_snippet() → Read implementations
3. trace_path() → Understand call chains
4. implement → Write the feature
```

### Before Major Refactoring
```
1. get_architecture() → Map components
2. trace_path(function_name="...", depth=3) → See all dependents
3. detect_changes(since="HEAD~5") → Understand recent patterns
4. refactor → Make changes with confidence
5. manage_adr() → Document why this trade-off was needed
```

### When Performance Optimization Needed
```
1. trace_path(mode="data_flow") → Understand argument flow
2. search_graph("convergence") → Find related optimizations
3. get_code_snippet() → Compare existing approaches
4. manage_adr() → Document optimization trade-offs
5. implement → Optimize with baseline documented
```

## Project-Specific Queries

**For solver/analysis work:**
```
search_graph("monte carlo")           # Find all Monte Carlo code
search_graph("equity")                # Equity calculations
search_graph("hand evaluation")       # Hand strength code
trace_path("calculate_odds")          # See who calls calculate_odds
```

**For database work:**
```
search_graph("sqlalchemy")            # ORM patterns
search_graph("session")               # Database session usage
trace_path("persist", mode="calls")   # Data persistence flow
```

**For GUI components:**
```
search_graph("handle_event")          # Event handler patterns
trace_path("draw")                    # Rendering flow
```

## Constraints
- Results are **read-only** (graph analysis only)
- `manage_adr()` is for documentation, not code decisions
- Always verify `search_graph()` results against actual code
- `detect_changes()` output can be large (use `depth` parameter to limit)
