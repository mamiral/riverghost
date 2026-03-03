# Feature Specification: All-In-or-Fold GTO Solver with Bonus Payouts

**Feature Branch**: `001-all-in-fold-gto`
**Created**: 2026-02-27
**Status**: Draft
**Input**: User description: "Add All-In-or-Fold GTO Solver with Bonus Payouts feature to HoPilot"

## Clarifications

### Session 2026-02-27
- Q: What is the primary GUI interaction pattern for the GTO solver? The spec mentions 'dedicated panels' but doesn't specify the user flow. → A: Basic
- Q: How are bonus payouts calculated? The spec mentions 'pot multipliers' in assumptions but acceptance scenarios suggest fixed amounts. → A: Variable
- Q: What specific algorithm should be used for range vs range optimization? The spec mentions 'Nash equilibrium' but doesn't specify the mathematical approach. → A: **Nash Equilibrium Algorithm** in the context of **poker GTO (Game Theory Optimal) opening ranges optimization** refers to computational methods that solve for **unexploitable preflop strategies**—ranges of hands to open-raise, shove, or limp from each position—that form part of a **Nash equilibrium** in the game.

  In poker terms:
  - **GTO opening ranges** are Nash-optimal if no opponent can gain EV by exploiting them (and vice versa), assuming perfect postflop play.
  - These are **optimized** via algorithms that iterate until strategies converge to equilibrium (exploitability ≈ 0).

  There are **two main contexts** (simplified vs. full-ring):

  ### 1. **Simplified Nash for Push-Fold/Open-Shove Ranges** (Tournaments, Short Stacks)
     - Common in MTTs near bubble/final table: Only **shove all-in or fold** preflop.
     - **Algorithm**: Exact Nash via **dynamic programming** or **linear programming** on the game matrix (EV calculations for all hand matchups, stacks, ICM).
       - Solves the zero-sum game directly: Find mixed strategies where each player's shove/call range is a best response to the other.
     - Tools: ICMIZER, HoldemResources Calculator (HRC), Simple Nash.
     - **How it works** (high-level):
       1. Input: Stack sizes, positions, payouts/ICM.
       2. Compute EV matrix for every hand vs. range.
       3. Iterate/induce indifference: Opponent must be indifferent to calling (EV_call = 0 vs. fold).
       4. Output: Nash shove % (e.g., SB shoves 42% vs. BB calls 14%).
     - **Example**: 10BB SB vs. BB: Nash = shove ~40-50% (suited connectors+, broadways, pairs), BB calls ~12-15% (QQ+, AK).

  ### 2. **Full GTO Opening Ranges** (Cash Games, Deeper Stacks)
     - Multi-street play: Open-raise sizing, limps, 3-bets, etc., abstracted into **buckets** (e.g., 1000 preflop combos).
     - **Core Algorithm**: **CFR (Counterfactual Regret Minimization)** and variants (CFR+, MC-CFR, CFRP)—the gold standard for approximating Nash in imperfect-info games like poker.
     - **Tools/Solvers**: PioSolver, GTO+, MonkerSolver, GTO Wizard, Pluribus/Libratus (AI).
     - **How CFR Optimizes Opening Ranges**:
       | Step | Description | Goal |
       |------|-------------|------|
       | **1. Abstraction** | Bucket similar hands/stacks (e.g., preflop: 169 hands → 50-200 buckets; postflop: bet sizes/actions limited). Define initial random ranges. | Make huge game tree solvable (~10^160 nodes → millions). |
       | **2. Traverse Tree** | Recursively simulate playthroughs (traversals) from root (preflop open). At each **infoset** (your info: hole cards, board, history), choose actions probabilistically. | Explore strategies. |
       | **3. Compute Regret** | For each action: **Counterfactual Regret** = (EV if taken) - (EV of avg strategy) * reach probability. Positive regret → action was good but not taken enough. | Measure "what if I deviated?" |
       | **4. Regret-Match** | Update strategy: Play actions proportional to positive regrets (avg strategy = weighted average over iterations). | Minimize future regret → converge to Nash. |
       | **5. Iterate** | Repeat 10k-1M+ times until **Nash Distance** < 0.01 mbb/g (exploitability). | Equilibrium: Best response to itself. |
       | **Output** | Preflop freqs: e.g., UTG open 14%: 100% AA, 80% AKs, 0% 72o. Mixed for bluffs/value. | Unexploitable ranges. |

     - **Preflop-Specific Optimization**:
       - Solvers often **seed** with rough ranges, solve postflop trees backward, refine preflop iteratively.
       - Multiway pots: Nash quirks (e.g., over-folding strong hands).
       - Result: Position-dependent (e.g., BTN opens 40-50%, CO 25%).

  ### Key Differences
  | Type | Use Case | Algorithm | Precision | Compute Time |
  |------|----------|-----------|-----------|--------------|
  | **Push-Fold Nash** | Short-stack MTTs | DP/Linear Prog | Exact | Seconds |
  | **Full GTO** | Cash/Deep MTTs | CFR Variants | Approximate (Nash dist. low) | Hours-Days (GPU cluster) |

  **Why Nash?** GTO = Nash: Unexploitable baseline. Deviate to exploit opponents.

  **Practical Tip**: Use precomputed charts (GTO Wizard library) or free Nash push-fold apps. Solvers for custom spots. CFR made poker AI beat pros (Pluratus).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic GTO Threshold Analysis (Priority: P1)

**As a poker player**, I want to input game parameters (number of opponents, pot size, bet amount, bonus payouts) and see the optimal equity threshold for all-in-or-fold decisions so I can understand GTO strategy for these simplified games.

**Why this priority**: This is the core functionality that delivers immediate value for analyzing all-in-or-fold tournament spots.

**Independent Test**: Can be fully tested by running the solver with specific parameters and verifying the calculated threshold matches expected GTO theory.

**Acceptance Scenarios**:

1. **Given** 8 opponents, $20 pot, $10 bet, standard bonus payouts, **When** solver calculates threshold, **Then** returns equity threshold between 0.0-1.0
2. **Given** custom bonus payouts, **When** solver runs, **Then** incorporates bonus multipliers in EV calculations
3. **Given** invalid parameters, **When** solver runs, **Then** returns appropriate error messages

---

### User Story 2 - Range Management and Persistence (Priority: P2)

**As a poker analyst**, I want to define, save, and load hero/villain opening ranges in YAML format so I can analyze specific range matchups in all-in-or-fold scenarios.

**Why this priority**: Range analysis is fundamental to poker strategy and enables advanced optimization features.

**Independent Test**: Can be fully tested by creating ranges, saving to YAML, loading them back, and verifying data integrity.

**Acceptance Scenarios**:

1. **Given** a range definition, **When** saved to YAML, **Then** file contains valid hand specifications
2. **Given** a YAML range file, **When** loaded, **Then** range object contains correct hands
3. **Given** invalid YAML, **When** loading, **Then** shows clear error messages

---

### User Story 3 - Interactive Strategy Visualization (Priority: P3)

**As a user**, I want to see which hands should be played vs folded with EV calculations and color-coded displays so I can quickly understand the optimal strategy.

**Why this priority**: Visual representation makes complex GTO concepts accessible to users.

**Independent Test**: Can be fully tested by generating strategy data and verifying correct visual representation.

**Acceptance Scenarios**:

1. **Given** GTO results, **When** displayed, **Then** profitable hands highlighted in green
2. **Given** hand selection, **When** clicked, **Then** shows detailed EV breakdown
3. **Given** strategy data, **When** exported, **Then** contains all relevant metrics

---

### User Story 4 - Range vs Range Optimization (Priority: P4)

**As an advanced user**, I want to optimize opening ranges against opponent ranges to find Nash equilibrium solutions for specific matchups in all-in-or-fold games using simplified push-fold Nash algorithms.

**Why this priority**: Enables advanced strategy development and tournament preparation.

**Independent Test**: Can be fully tested by providing two ranges and verifying Nash equilibrium solutions are found using dynamic programming or linear programming approaches.

**Acceptance Scenarios**:

1. **Given** hero and villain ranges, **When** optimized using push-fold Nash, **Then** returns Nash equilibrium ranges for both players with shove frequencies and call ranges
2. **Given** asymmetric ranges with different stack sizes, **When** solved, **Then** accounts for stack size differences in equilibrium calculation using ICM considerations
3. **Given** complex range interactions, **When** solved using dynamic programming, **Then** finds stable Nash equilibrium strategies where neither player can exploit the other

---

### User Story 5 - GUI Integration (Priority: P5)

**As a user**, I want the GTO solver integrated into the main HoPilot GUI with a simple form interface (parameter inputs, calculate button, results display) so I can access advanced analysis without command-line usage.

**Why this priority**: Makes the feature accessible to the target user base through the existing interface.

**Independent Test**: Can be fully tested by interacting with GUI elements and verifying correct solver integration.

**Acceptance Scenarios**:

1. **Given** main GUI, **When** GTO panel opened, **Then** shows parameter input form with opponents, pot size, bet amount, bonus payout controls
2. **Given** parameters entered, **When** calculate button clicked, **Then** displays results in simple results display area
3. **Given** range files, **When** loaded via GUI file picker, **Then** populates range selection dropdowns

---

### Edge Cases

- What happens when bonus payouts create negative EV for all hands?
- How does system handle ranges with conflicting hands?
- What happens when YAML files contain invalid hand specifications?
- How does system behave with very large ranges (1000+ hands)?
- What happens when simulation parameters create impossible scenarios?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST calculate GTO equity thresholds for all-in-or-fold games
- **FR-002**: System MUST support custom bonus payout configurations
- **FR-003**: System MUST load and save ranges in YAML format
- **FR-004**: System MUST provide visual strategy representation
- **FR-005**: System MUST integrate with existing CardAssignmentManager for range validation
- **FR-006**: System MUST handle range vs range optimization
- **FR-007**: System MUST provide GUI panels for parameter input and result display
- **FR-008**: System MUST validate YAML range file syntax
- **FR-009**: System MUST support progressive calculation with progress indicators
- **FR-010**: System MUST cache calculation results for performance

### Key Entities *(include if feature involves data)*

- **Range**: Collection of poker hands with metadata (name, description, hand list)
- **GTO_Result**: Calculation output containing threshold, optimal hands, EV data
- **Bonus_Config**: Multiplier mappings for different hand categories
- **Game_Parameters**: Opponents, pot size, bet amount, simulation settings

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can compute GTO strategies for all-in-or-fold games in under 30 seconds
- **SC-002**: System correctly incorporates bonus payouts in EV calculations
- **SC-003**: Range files load/save without data corruption
- **SC-004**: GUI provides intuitive access to GTO analysis for 90% of users
- **SC-005**: Advanced users can optimize ranges vs ranges successfully
- **SC-006**: System handles edge cases gracefully without crashes

## Assumptions

- Users understand basic poker concepts (equity, ranges, EV)
- Monte Carlo simulation provides sufficient accuracy for GTO approximation
- YAML format is acceptable for range persistence
- GUI integration follows existing HoPilot patterns with simple form-based interface
- Bonus payouts are calculated variably by hand type and game rules (pot multipliers, fixed amounts, or percentages as appropriate)
- Range vs range optimization uses simplified push-fold Nash algorithms (dynamic programming/linear programming) suitable for all-in-or-fold games, not full CFR solvers

## Dependencies

- Existing PokerAnalyzer for equity calculations
- HandRange for range parsing and expansion
- Pygame for GUI components
- PyYAML for range file handling

## Out of Scope

- Full GTO solver for betting games (only all-in-or-fold)
- Real-time opponent adaptation
- Multi-street analysis
- Integration with external poker sites
