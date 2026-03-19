"""State machine diagram utilities for HoPilot."""

import os
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


def generate_gui_run_state_diagram(output_dir: str = None) -> str:
    """Generate mermaid diagram for the precompute GuiRunState state machine.
    
    Creates a mermaid-compatible state diagram showing all precompute states
    and valid transitions used by AoFPrecomputeRunner.
    
    **Args**:
        output_dir: Optional directory to save markdown file. If None, only returns diagram.
    
    **Returns**:
        Mermaid diagram source code (string)
    
    **Usage**:
    ```python
    diagram = generate_gui_run_state_diagram()
    print(diagram)  # Display mermaid diagram
    
    # Or save to file
    generate_gui_run_state_diagram(output_dir="docs/")
    ```
    """
    try:
        from hopilot.gto.aof_precompute_runner import GuiRunState, _GUI_TRANSITIONS
    except ImportError:
        logger.error("Could not import GuiRunState from aof_precompute_runner")
        return ""
    
    try:
        # Build mermaid state diagram from transition matrix
        mermaid_lines = [
            "stateDiagram-v2",
            "    [*] --> IDLE",
            ""
        ]
        
        # Add transitions from the _GUI_TRANSITIONS matrix
        for source_state, target_states in _GUI_TRANSITIONS.items():
            for target_state in target_states:
                mermaid_lines.append(f"    {source_state.value} --> {target_state.value}")
        
        # Mark terminal-like states (can go back to IDLE or RUNNING)
        mermaid_lines.extend([
            "",
            "    COMPLETED --> [*]",
            "    FAILED --> [*]",
        ])
        
        diagram_source = "\n".join(mermaid_lines)
        logger.debug("GuiRunState diagram generated successfully")
        
        # Optionally save to markdown file
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            markdown_content = f"""# AoF Precompute State Machine (GuiRunState)

## State Machine Diagram

The actual precompute engine state machine used in `aof_precompute_runner.py`.

```mermaid
{diagram_source}
```

## States

- **IDLE** (initial): Ready to start precompute
- **RUNNING**: Actively computing cells with worker threads
- **PAUSED**: Paused, can resume or stop
- **STOPPING**: Transitioning to stop (intermediate state)
- **COMPLETED**: Computation finished successfully
- **FAILED**: Computation encountered an error

## Transitions

Precompute follow this state machine:
- `IDLE` -> `RUNNING` (start precompute)
- `RUNNING` -> `PAUSED` (pause), `STOPPING` (prepare stop), `COMPLETED` (finished), `FAILED` (error)
- `PAUSED` -> `RUNNING` (resume), `IDLE` (reset), `COMPLETED` (complete anyway), `FAILED` (error)
- `STOPPING` -> `PAUSED` (went back to paused), `COMPLETED` (finished stopping), `FAILED` (error during stop)
- `COMPLETED` -> `IDLE` (reset), `RUNNING` (start new precompute)
- `FAILED` -> `IDLE` (reset), `RUNNING` (retry)

## Comparison with SimulationState Controller

The `SimulationState` state machine (in `state_machine_config.py`) is a **wrapper** that:
- Manages the overall simulation lifecycle
- Provides callbacks for validation, resource allocation, error handling
- Coordinates with `GuiRunState` through the `aof_browser_panel.py`
- Adds audit trail, session management, and pause/resume validation

`SimulationState` -> controls -> `GuiRunState` (via AoFBrowserPanel)

## Implementation

See `aof_precompute_runner.py` for the GuiRunState enum and `_GUI_TRANSITIONS` matrix.
"""
            
            filepath = os.path.join(output_dir, "gui_precompute_state_diagram.md")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            logger.info(f"GuiRunState diagram saved to {filepath}")
        
        return diagram_source
        
    except Exception as e:
        logger.error(f"Failed to generate GuiRunState diagram: {e}", exc_info=True)
        return ""


if __name__ == "__main__":
    # Generate and display GuiRunState diagram
    diagram = generate_gui_run_state_diagram(output_dir="docs")
    if diagram:
        print("\n" + "="*80)
        print("GUI PRECOMPUTE STATE MACHINE DIAGRAM (Mermaid Format)")
        print("="*80)
        print(diagram)
        print("="*80 + "\n")
        print("✓ Diagram saved to docs/gui_precompute_state_diagram.md")
    else:
        print("✗ Failed to generate diagram")
