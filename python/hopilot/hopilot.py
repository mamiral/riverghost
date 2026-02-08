import logging
import os
import sys
import threading
import time
from logging.handlers import RotatingFileHandler

import cv2
import dxcam
import pygetwindow as gw
import win32gui

# Add the parent directory to the path to import hopilot modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hopilot.card_detector import CardDetector
from hopilot.dashboard import Dashboard
from hopilot.poker_analyzer import PokerAnalyzer


def setup_logging(log_level=logging.INFO):
    """
    Set up logging configuration with console and rotating file handlers.

    Args:
        log_level: Logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Rotating file handler (128MB max size, keep 5 backup files)
    log_file = os.path.join(log_dir, "hopilot.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=128 * 1024 * 1024, backupCount=5  # 128MB
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Log the setup
    logger.info("Logging initialized")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")


# Initialize logging
setup_logging()


def list_visible_windows():
    """Print all visible window titles to help find the correct one"""
    logger = logging.getLogger(__name__)
    logger.info("Listing all visible windows")
    logger.info("Visible windows:")

    def enum_handler(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                logger.info(f"  - {title} (HWND: {hwnd})")

    win32gui.EnumWindows(enum_handler, None)
    logger.info("Window listing completed")


def get_window_coords(window_title):
    """
    Get window coordinates (left, top, right, bottom) by title.
    Tries exact match first, then partial via pygetwindow.
    Returns (left, top, right, bottom) or None if not found.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Searching for window: '{window_title}'")

    if not window_title or not isinstance(window_title, str):
        logger.error("Invalid window title provided")
        return None

    try:
        # Try exact match with win32gui
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            logger.info(f"Found exact match: '{window_title}' at {rect}")
            return rect  # (left, top, right, bottom)

        # Fallback: partial match with pygetwindow
        logger.debug("Exact match failed, trying partial match with pygetwindow")
        windows = gw.getWindowsWithTitle(window_title)
        if windows:
            win = windows[0]
            left, top, width, height = win.left, win.top, win.width, win.height
            right = left + width
            bottom = top + height
            rect = (left, top, right, bottom)
            logger.info(f"Found partial match: '{win.title}' at {rect}")
            return rect

        logger.error(f"No window found matching '{window_title}'")
        logger.info("Tip: Run list_visible_windows() to see titles.")
        return None

    except Exception as e:
        logger.error(f"Error getting window coordinates: {e}")
        return None


def capture_with_dxcam(region):
    """Capture using DXcam (fast, GPU-friendly)"""
    logger = logging.getLogger(__name__)

    if region is None:
        logger.warning("Capture region is None")
        return None

    logger.debug(f"Starting DXcam capture for region: {region}")

    # DXcam expects (left, top, right, bottom)
    try:
        camera = dxcam.create(output_idx=0, output_color="BGR")
        if camera is None:
            logger.error("DXcam failed to initialize. Check GPU/drivers.")
            return None

        frame = camera.grab(region=region)
        if frame is None:
            logger.warning("DXcam capture returned None frame")
            return None

        logger.debug(f"Successfully captured frame of shape: {frame.shape}")
        return frame

    except Exception as e:
        logger.error(f"Error during DXcam capture: {e}")
        return None

    finally:
        try:
            camera.release()  # Important: release after each grab in loop
            logger.debug("DXcam camera released")
        except Exception:
            logger.warning("Failed to release DXcam camera")


class HoPilot:
    def __init__(self, window_title):
        logger = logging.getLogger(__name__)
        logger.info(f"Initializing HoPilot for window: '{window_title}'")

        try:
            self.detector = CardDetector()
            self.analyzer = PokerAnalyzer()
            self.dashboard = Dashboard()
            self.window_title = window_title

            logger.info("Components initialized successfully")

            self.region = get_window_coords(window_title)
            if self.region is None:
                logger.error(
                    f"Window '{window_title}' not found - cannot initialize HoPilot"
                )
                raise ValueError(f"Window '{window_title}' not found")

            logger.info(f"Window region set to: {self.region}")

            self.current_assignments = {}
            self.phase = "pre-flop"  # Default phase
            self.lock = threading.Lock()
            self.current_frame = None
            self.video_writer = None

            logger.info("HoPilot initialization completed successfully")

        except Exception as e:
            logger.error(f"Failed to initialize HoPilot: {e}")
            raise

    def determine_phase(self, assignments):
        """
        Determine game phase based on detected board cards.
        """
        logger = logging.getLogger(__name__)
        board_count = sum(
            1
            for slot in ["flop_1", "flop_2", "flop_3", "turn", "river"]
            if assignments.get(slot)
        )

        if board_count == 0:
            phase = "pre-flop"
        elif board_count <= 3:
            phase = "flop"
        elif board_count == 4:
            phase = "turn"
        else:
            phase = "river"

        logger.debug(f"Determined phase: {phase} (board cards detected: {board_count})")
        return phase

    def get_current_assignments(self):
        logger = logging.getLogger(__name__)
        with self.lock:
            assignments = self.current_assignments.copy()
            logger.debug(f"Retrieved current assignments: {len(assignments)} positions")
            return assignments

    def get_advice(self):
        logger = logging.getLogger(__name__)

        hole_cards = []
        if self.current_assignments.get("hero_hole_1"):
            hole_cards.append(self.current_assignments["hero_hole_1"][0])
        if self.current_assignments.get("hero_hole_2"):
            hole_cards.append(self.current_assignments["hero_hole_2"][0])

        board_cards = []
        for slot in ["flop_1", "flop_2", "flop_3", "turn", "river"]:
            if self.current_assignments.get(slot):
                board_cards.append(self.current_assignments[slot][0])

        logger.debug(
            f"Getting advice for hole_cards={hole_cards}, board_cards={board_cards}, phase={self.phase}"
        )

        try:
            advice = self.analyzer.get_advice(hole_cards, board_cards, self.phase)
            logger.debug(f"Generated advice: {advice}")
            return advice
        except Exception as e:
            logger.error(f"Error getting advice: {e}")
            return "Error generating advice"

    def get_current_image_path(self):
        logger = logging.getLogger(__name__)
        path = getattr(self, "current_image_path", None)
        logger.debug(f"Retrieved current image path: {path}")
        return path

    def toggle_recording(self, start):
        logger = logging.getLogger(__name__)
        if start:
            if self.video_writer is None:
                os.makedirs("recordings", exist_ok=True)
                files = os.listdir("recordings")
                avi_files = [f for f in files if f.endswith(".avi")]
                numbers = []
                for f in avi_files:
                    try:
                        num = int(f[:-4])
                        numbers.append(num)
                    except ValueError:
                        pass
                next_num = max(numbers) + 1 if numbers else 1
                video_path = f"recordings/{next_num}.avi"
                fourcc = cv2.VideoWriter_fourcc(*"MJPG")
                fps = 30
                height, width = (
                    self.region[3] - self.region[1],
                    self.region[2] - self.region[0],
                )
                self.video_writer = cv2.VideoWriter(
                    video_path, fourcc, fps, (width, height)
                )
                logger.info(f"Started recording to {video_path}")
        else:
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
                logger.info("Stopped recording")

    def process_frame(self, image):
        logger = logging.getLogger(__name__)
        logger.debug("Processing frame for card detection")

        try:
            assignments = self.detector.detect_cards(image)
            detected_count = sum(1 for v in assignments.values() if v is not None)
            logger.debug(f"Card detection completed: {detected_count} cards detected")

            with self.lock:
                self.current_assignments = assignments
                self.phase = self.determine_phase(self.current_assignments)
                self.current_image_path = image if isinstance(image, str) else None

            logger.debug(f"Frame processing completed - phase: {self.phase}")
        except Exception as e:
            logger.error(f"Error processing frame: {e}")

    def run_with_capture(self):
        logger = logging.getLogger(__name__)
        logger.info("Starting HoPilot with live capture mode")

        def process_frames():
            frame_delay = 0.033  # ~30fps
            frame_interval = 5
            frame_count = 0

            while True:
                try:
                    with self.dashboard.speed_lock:
                        if self.dashboard.paused:
                            time.sleep(0.1)
                            continue

                    frame = capture_with_dxcam(self.region)
                    if frame is None:
                        logger.warning("Capture failed - retrying in 1s...")
                        time.sleep(1)
                        continue

                    self.current_frame = frame
                    logger.debug(f"Captured frame of shape: {frame.shape}")

                    if self.video_writer:
                        self.video_writer.write(frame)
                        logger.debug("Frame written to video")

                    frame_count += 1
                    if frame_count % frame_interval == 0:
                        self.process_frame(frame)

                        with self.dashboard.speed_lock:
                            if self.dashboard.slow_down:
                                delay = (
                                    frame_delay * frame_interval / self.dashboard.speed
                                )
                                logger.debug(f"Slowing down processing by {delay:.3f}s")
                                time.sleep(delay)

                except Exception as e:
                    logger.error(f"Error in frame processing loop: {e}")
                    time.sleep(1)  # Prevent tight error loops

        try:
            processing_thread = threading.Thread(target=process_frames)
            processing_thread.daemon = True
            processing_thread.start()
            logger.info("Frame processing thread started")

            self.dashboard.run(
                self.get_current_assignments,
                self.get_advice,
                self.get_current_image_path,
                dir_mode=False,
                video_mode=True,
                frame_func=lambda: self.current_frame,
                recording_toggle_func=lambda start: self.toggle_recording(start),
                game_mode="rush_n_cash",
            )

        except Exception as e:
            logger.error(f"Error in run_with_capture: {e}")
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HoPilot Poker Copilot")
    parser.add_argument("--window-title", help="Title of the window to capture")
    parser.add_argument("--replay-video", help="Path to video file to replay")
    args = parser.parse_args()

    if args.replay_video:
        # Create detector for replay mode
        detector = CardDetector()
        analyzer = PokerAnalyzer()
        dashboard = Dashboard()

        # Track current assignments for replay
        replay_state = {"assignments": {}, "phase": "pre-flop"}

        def get_replay_assignments():
            return replay_state["assignments"].copy()

        def get_replay_advice():
            hole_cards = []
            if replay_state["assignments"].get("hero_hole_1"):
                hole_cards.append(replay_state["assignments"]["hero_hole_1"][0])
            if replay_state["assignments"].get("hero_hole_2"):
                hole_cards.append(replay_state["assignments"]["hero_hole_2"][0])

            board_cards = []
            for slot in ["flop_1", "flop_2", "flop_3", "turn", "river"]:
                if replay_state["assignments"].get(slot):
                    board_cards.append(replay_state["assignments"][slot][0])

            return analyzer.get_advice(hole_cards, board_cards, replay_state["phase"])

        def process_replay_frame(frame):
            replay_state["assignments"] = detector.detect_cards(frame)
            board_count = sum(
                1
                for slot in ["flop_1", "flop_2", "flop_3", "turn", "river"]
                if replay_state["assignments"].get(slot)
            )
            if board_count == 0:
                replay_state["phase"] = "pre-flop"
            elif board_count <= 3:
                replay_state["phase"] = "flop"
            elif board_count == 4:
                replay_state["phase"] = "turn"
            else:
                replay_state["phase"] = "river"

        dashboard.run(
            get_replay_assignments,
            get_replay_advice,
            lambda: args.replay_video,
            dir_mode=False,
            video_mode=True,
            frame_func=None,
            recording_toggle_func=None,
            replay_mode=True,
            video_path=args.replay_video,
            frame_processor=process_replay_frame,
            game_mode="rush_n_cash",
        )
    else:
        pilot = HoPilot(args.window_title)
        pilot.run_with_capture()
