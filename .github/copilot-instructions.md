# FORCE Principles

**Meta-principles for interaction: applied to every response, explanation, and decision.**

## Never Soften Criticism
- Say directly: *"This fails because X"* not *"Have you considered X?"*
- Name the flaw explicitly instead of hedging
- Protect correctness over ego; clarity beats politeness

## Say So Directly
- Don't suggest indirectly—state the problem outright
- *"This won't work because Y"* beats *"Hmm, that might not..."*
- Eliminate qualifying language ("perhaps," "maybe," "could")

## Surface Uncertainty
- Admit when unsure: *"I'm uncertain about Y—need to verify"* vs. confident speculation
- Don't present guesses as facts
- Mark verification gaps explicitly

## Don't Assume Intent
- Prompt the user directly instead of guessing what they want
- Ask before inferring requirements
- Clarify ambiguity rather than resolving it silently

## Explain Future Actions
- State what you'll do before executing changes
- Never surprise with unexplained edits
- If refactoring, say why before doing it

---

# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Apply these to all work—writing, reviewing, refactoring.

## 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**

- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them—don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If code exceeds 200 lines and could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it—don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan with verify checks at each step.

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

# Implementation Quality Standards

**Non-negotiable standards for code merged into the project.**

## Complete Implementation Only

- **No scaffolding masquerading as implementation**
  - If code contains `TODO`, `FIXME`, or comments like "This will be implemented later"—it is NOT implemented
  - TODOs belong in GitHub issues, not in merged code
  - Placeholder logic waiting for "real logic" is incomplete work
  - Incomplete code should not pass review or be committed

- **"Real implementation" means end-to-end working code**
  - All features must be complete and functional on merge
  - No "Phase 2" implementations, no "will be finished later"
  - If you can't finish it now, open an issue and don't start it
  - Code reviewers must verify: Can this feature be used immediately, or is it broken without future work?

## Testing Must Validate Real Behavior

- **Tests check actual implementation outcomes, never just mocks**
  - Mock-based tests that pass with fake implementations are worthless
  - Every test must fail if you delete the real implementation
  - Test the behavior, not the internal call structure
  - Example: Don't test `assert mock.called`. Test `assert result == expected_value`

- **All assertions must be meaningful**
  - Never use assertions like `assert True`, `assert obj is not None`, or `assert func_called`
  - Assertions must validate actual correctness, not just "code executed"
  - Each assertion should describe a real requirement

- **Never write placeholder tests**
  - No `pass` statements in test bodies
  - No incomplete test logic that will "be filled in later"
  - No tests that check mocks instead of real outputs
  - If you can't write the test, the feature isn't clear enough

## Verify Before Declaring Done

- Run full test suite before merging
- All tests must pass with REAL implementation
- If tests pass only because they check mocks, they don't count
- Code with TODOs is not done—period

---

# Architecture Constraints

**System-wide decisions that apply to every component, discussion, and design choice.**

## GameStates-First: Solver Writes Raw Data Only

The database is **GameStates-first**. The solver's only job is to write raw simulation data. Aggregation is a separate post-processing phase.

- **Solver writes**: one `GameState` row per simulation iteration — player hole cards, board cards, bets, hand resolution (`hand_rank`, `hand_class`, `final_strength`), outcome
- **Solver does NOT**: compute equity, win rate, EV, or any aggregated metric
- **Post-processing reads**: `GameState` rows from DB, groups by hand matchup, derives `MatrixCell` and `AggregatedMetric` records

**Violations to reject outright:**
- Adding `equity = wins / total` anywhere in the solver
- Returning aggregated dicts from simulation loops
- Creating `MatrixCell` records during solver runs

## GameState Has No Cell Reference at Write Time

`GameState.cell_id` does not exist. The solver does not know which matrix cell it is computing.

- Cell identity is resolved in post-processing by inspecting `Player.hole_cards` from stored `GameState` records
- Never add `cell_id`, `matrix_id`, or any matrix FK to `GameState`

## Persistence Uses Strategy Pattern

The solver receives a `GameStatePersistence` strategy via constructor injection. It never instantiates storage directly.

- `DatabasePersistenceStrategy` — production (SQLAlchemy)
- `MockPersistenceStrategy` — unit tests
- `InMemoryPersistenceStrategy` — development/prototyping

Concrete strategies live in `python/hopilot/database/persistence/`. The abstract interface is `GameStatePersistence` in `base.py`. Do not bypass the strategy interface with direct DB calls inside the solver.

## Prototyping Folder Is Design Validation, Not Production Code

Scripts in `prototyping/` exist to validate schema design and ORM patterns. They use test data, not real solver output. Do not import from `prototyping/` in production code. The canonical ORM models live in `python/hopilot/models/`.
