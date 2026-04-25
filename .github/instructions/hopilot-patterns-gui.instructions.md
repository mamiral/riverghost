---
description: "Use when implementing HoPilot GUI components, handling events, or working with pygame-based interfaces. Covers component architecture, event handling, and rendering."
applyTo: "gui_components/**"
---

# HoPilot GUI Component Patterns

## Component Architecture
- All components inherit from base `Component` class
- Each component has a standard interface: `handle_event()`, `draw()`, `update()`
- Components are modular and composable
- Store state internally; emit events/actions to parent

## Event Handling
- Implement `handle_event()` to process input events
- Return `True` if event was consumed, `False` if not handled (passes to parent)
- Keep event handling logic simple—delegate complex logic to parent loop
- Example: CardPicker.handle_event() checks mouse clicks, returns True if card clicked

## Drawing & Rendering

## Drawing & Rendering
- Implement `draw(surface)` to render component to pygame surface
- Draw order matters: background → components → modals → overlays
- Call parent's draw() first, then component-specific drawing
- Don't modify global pygame state; clean up after drawing

## Draw Order Convention
1. **Background/base components** (cards, buttons, text)
2. **Overlay components** (ranges, stats)
3. **Modal dialogs** (card picker, confirmation)
4. **Results/HUD** (equity, recommendations)

## State Management
- Initialize all state in `__init__()`
- Use `update()` for frame-based state changes (animations, timing)
- Keep state local to component; use parent for shared state
- Document state transitions for complex components

## Integration with Main Loop
```python
# Typical component usage in main loop
for event in pygame.event.get():
    if component.handle_event(event):
        # Event was consumed by component
        continue
    # Handle event in main loop if component didn't consume it

component.update(dt)
component.draw(surface)
pygame.display.flip()
```

Real example: [CardPicker.handle_event()](python/hopilot/gui_components/card_picker.py#L99) returns True when card clicked

## Modal Overlays
- Card picker and dialogs are modal overlays
- Modal should consume all events until dismissed
- Return action when modal completes (success, cancel, etc.)
- Parent should check for modal first before routing events
