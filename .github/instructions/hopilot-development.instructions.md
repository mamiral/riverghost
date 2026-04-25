---
description: "Use when setting up HoPilot development environment, running the application, or debugging. Covers workflows, dependencies, and troubleshooting."
---

# HoPilot Development Workflows

## Environment Setup
- **OS**: Windows (all commands use PowerShell)
- **Python**: Virtual environment (venv)
- **Setup**: `python -m venv .venv && .venv\Scripts\Activate.ps1`
- **Install**: `pip install -r requirements.txt`

## Running the Application
All Python commands must be run from within the activated virtual environment:

```bash
# Activate venv first
.venv\Scripts\activate  # Windows PowerShell
# or
.venv\Scripts\Activate.ps1  # Windows PowerShell alternative

# Then run from python/ directory
cd python
python -m hopilot.hopilot "PokerStars"  # Real-time analysis
python -m hopilot.poker_simulator_gui  # Interactive simulator
```

## Adding New Features
1. Create modular components in `hopilot/` or `gui_components/`
2. Add configuration in `config.py` if needed
3. Write tests in `tests/`
4. Update logging and error handling
5. Document in `plans/` or `docs/`

## Debugging
- Check logs in `python/hopilot/logs/hopilot.log`
- Use `list_visible_windows()` to find window titles
- Test card detection with sample images in `validation/`
- GUI debugging: add print statements, check event handling
- Enable DEBUG logging to trace execution flow

## Dependencies
- **Windows-specific**: dxcam, pywin32 (screen capture)
- **Computer Vision**: opencv-python, numpy
- **GUI**: pygame
- **Poker Analysis**: treys
- **Configuration**: pydantic
- **Complete list**: See requirements.txt

## Common Pitfalls
- Always run from `python/` directory for imports
- GUI apps need display environment—test in isolation if headless
- Card detection requires calibrated templates—validate on target platform
- Cache database persists between runs for performance—clear if behavior changes
- Threading used for real-time capture—handle locks properly to avoid race conditions
