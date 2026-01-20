# Poker Hold'em Copilot Application Design Plan

## Overview
A Python application that serves as a copilot for Texas Hold'em poker games. It detects cards from game screenshots or video feeds using YOLO object detection, displays player hole cards and community board cards, and provides strategic advice based on the game phase.

## Architecture

### Core Components
1. **Card Detection Module**
   - Uses YOLOv8 model for card recognition
   - Processes images to detect playing cards
   - Assigns detected cards to poker positions (hole cards, flop, turn, river)

2. **Poker Analysis Engine**
   - Evaluates hand strength
   - Calculates odds and probabilities
   - Provides betting recommendations

3. **Dashboard GUI**
   - Built with Pygame for game-like interface
   - Displays detected cards visually
   - Shows analysis results and advice
   - Updates in real-time as game progresses

4. **Image Capture System**
   - Supports static image processing
   - Processes video files using ffmpeg (e.g., recordings/sng_better.mp4)
   - Can be extended for real-time screen capture or live streams

### Game Phases and Features
- **Pre-flop**: Display hole cards, basic hand analysis
- **Flop**: Show community cards, hand strength vs range
- **Turn**: Updated odds, position-based advice
- **River**: Final hand evaluation, decision recommendations

### Technical Stack
- Python 3.x
- ultralytics YOLO for card detection
- Pygame for GUI/dashboard
- OpenCV/Pillow for image processing
- Poker evaluation library (to be determined)

### File Structure
```
python/
├── poker_copilot.py          # Main application
├── card_detector.py          # Card detection logic
├── poker_analyzer.py         # Hand analysis
├── dashboard.py              # Pygame GUI
├── card_layout.py            # Existing layout system
└── utils.py                  # Helper functions
```

### Implementation Steps
1. Analyze requirements and define app architecture
2. Choose and set up GUI framework (Pygame)
3. Integrate card detection from prototype
4. Implement card display on dashboard
5. Add poker hand evaluation logic
6. Implement phase-based advice system
7. Add real-time image capture functionality
8. Create main application loop
9. Test with sample images
10. Refine UI and add features

### Assumptions
- App runs on desktop environment
- Images/videos provided by user or captured from screen
- Basic poker knowledge assumed for advice interpretation
- YOLO model accuracy sufficient for card detection
- Pygame suitable for dashboard visualization

### Future Enhancements
- Real-time video processing
- Multi-table support
- Advanced AI-driven strategy suggestions
- Integration with poker tracking software