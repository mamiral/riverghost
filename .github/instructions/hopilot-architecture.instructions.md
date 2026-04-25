---
description: "Use when understanding HoPilot architecture, designing new components, or working with core systems."
---

# HoPilot Architecture

## Overview
HoPilot is a real-time poker analysis tool that captures poker game screenshots, detects cards using computer vision, and calculates odds using Monte Carlo simulations. The application consists of modular components for card detection, analysis, and GUI interfaces.

## Core Components

### Card Detection
- **Module**: `card_detector.py`
- **Technology**: OpenCV-based template matching
- **Purpose**: Extract card faces from poker table screenshots
- **Key operations**: Template matching, card layout detection, confidence scoring

### Analysis Engine
- **Module**: `poker_analyzer.py`
- **Technology**: Monte Carlo simulations using `treys` library
- **Purpose**: Calculate hand equity, probability distributions, and GTO recommendations
- **Key operations**: Range analysis, equity calculation, simulation convergence

### GUI Components
- **Module**: `gui_components/`
- **Technology**: Pygame-based widgets
- **Purpose**: Reusable UI elements for interactive analysis
- **Key patterns**: Event-driven, modal overlays, draw order management

### Configuration System
- **Module**: `config.py`
- **Technology**: Pydantic-validated YAML
- **Purpose**: Centralized game mode, seat, and analysis settings
- **Key structure**: `game_modes` → `slots` → card positions and role definitions

### Real-time Capture
- **Module**: `hopilot.py`
- **Technology**: Windows screen capture using `dxcam`
- **Purpose**: Continuous monitoring of poker table state
- **Key challenge**: Threading and frame synchronization

### Logging & Monitoring
- **Module**: `logging_config.py`
- **Purpose**: Unified logging across all modules
- **Design**: Single initialization, per-module logger instances

## Design Principles
- **Modularity**: Each component has a single responsibility
- **Configuration-driven**: Game modes and layouts are data, not code
- **Real-time first**: Designed for continuous operation with minimal latency
- **Windows-native**: Leverages Windows APIs for reliability
