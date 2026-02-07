import cv2
import time
import threading
import win32gui
import numpy as np
import dxcam
import pygetwindow as gw
import os
from card_detector import CardDetector
from poker_analyzer import PokerAnalyzer
from dashboard import Dashboard

def list_visible_windows():
    """Print all visible window titles to help find the correct one"""
    print("Visible windows:")
    def enum_handler(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                print(f"  - {title} (HWND: {hwnd})")
    win32gui.EnumWindows(enum_handler, None)


def get_window_coords(window_title):
    """
    Get window coordinates (left, top, right, bottom) by title.
    Tries exact match first, then partial via pygetwindow.
    Returns (left, top, right, bottom) or None if not found.
    """
    # Try exact match with win32gui
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd:
        rect = win32gui.GetWindowRect(hwnd)
        print(f"Found exact match: '{window_title}'")
        return rect  # (left, top, right, bottom)

    # Fallback: partial match with pygetwindow
    windows = gw.getWindowsWithTitle(window_title)
    if windows:
        win = windows[0]
        left, top, width, height = win.left, win.top, win.width, win.height
        right = left + width
        bottom = top + height
        print(f"Found partial match: '{win.title}'")
        return (left, top, right, bottom)

    print(f"No window found matching '{window_title}'")
    print("Tip: Run list_visible_windows() to see titles.")
    return None


def capture_with_dxcam(region):
    """Capture using DXcam (fast, GPU-friendly)"""
    if region is None:
        return None

    # DXcam expects (left, top, right, bottom)
    camera = dxcam.create(output_idx=0, output_color="BGR")
    if camera is None:
        print("DXcam failed to initialize. Check GPU/drivers.")
        return None

    try:
        frame = camera.grab(region=region)
        if frame is None:
            print("Capture returned None.")
            return None

        # DXcam usually returns correct orientation (no flip needed)
        # But if flipped, uncomment:
        # frame = cv2.flip(frame, 0)  # vertical
        # frame = cv2.flip(frame, 1)  # horizontal
        # frame = cv2.flip(frame, -1) # both

        return frame

    finally:
        camera.release()  # Important: release after each grab in loop


class HoPilot:
    def __init__(self, window_title):
        self.detector = CardDetector()
        self.analyzer = PokerAnalyzer()
        self.dashboard = Dashboard()
        self.window_title = window_title
        self.region = get_window_coords(window_title)
        if self.region is None:
            raise ValueError(f"Window '{window_title}' not found")
        self.current_assignments = {}
        self.phase = 'pre-flop'  # Default phase
        self.lock = threading.Lock()
        self.current_frame = None
        self.video_writer = None


    def determine_phase(self, assignments):
        """
        Determine game phase based on detected board cards.
        """
        board_count = sum(1 for slot in ['flop_1', 'flop_2', 'flop_3', 'turn', 'river'] if assignments.get(slot))
        if board_count == 0:
            return 'pre-flop'
        elif board_count <= 3:
            return 'flop'
        elif board_count == 4:
            return 'turn'
        else:
            return 'river'

    def get_current_assignments(self):
        with self.lock:
            return self.current_assignments.copy()

    def get_advice(self):
        hole_cards = []
        if self.current_assignments.get('hero_hole_1'):
            hole_cards.append(self.current_assignments['hero_hole_1'][0])
        if self.current_assignments.get('hero_hole_2'):
            hole_cards.append(self.current_assignments['hero_hole_2'][0])

        board_cards = []
        for slot in ['flop_1', 'flop_2', 'flop_3', 'turn', 'river']:
            if self.current_assignments.get(slot):
                board_cards.append(self.current_assignments[slot][0])

        return self.analyzer.get_advice(hole_cards, board_cards, self.phase)

    def get_current_image_path(self):
        return getattr(self, 'current_image_path', None)

    def toggle_recording(self, start):
        if start:
            if self.video_writer is None:
                os.makedirs('recordings', exist_ok=True)
                files = os.listdir('recordings')
                avi_files = [f for f in files if f.endswith('.avi')]
                numbers = []
                for f in avi_files:
                    try:
                        num = int(f[:-4])
                        numbers.append(num)
                    except ValueError:
                        pass
                next_num = max(numbers) + 1 if numbers else 1
                video_path = f'recordings/{next_num}.avi'
                fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                fps = 30
                height, width = self.region[3] - self.region[1], self.region[2] - self.region[0]
                self.video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
                print(f"Started recording to {video_path}")
        else:
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
                print("Stopped recording")

    def process_frame(self, image):
        assignments = self.detector.detect_cards(image)
        with self.lock:
            self.current_assignments = assignments
            self.phase = self.determine_phase(self.current_assignments)
            self.current_image_path = image if isinstance(image, str) else None

    def run_with_capture(self):
        def process_frames():
            frame_delay = 0.033  # ~30fps
            frame_interval = 5
            frame_count = 0
            while True:
                with self.dashboard.speed_lock:
                    if self.dashboard.paused:
                        time.sleep(0.1)
                        continue

                frame = capture_with_dxcam(self.region)
                if frame is None:
                    print("Capture failed - retrying in 1s...")
                    time.sleep(1)
                    continue

                self.current_frame = frame

                if self.video_writer:
                    self.video_writer.write(frame)

                frame_count += 1
                if frame_count % frame_interval == 0:
                    self.process_frame(frame)

                    with self.dashboard.speed_lock:
                        if self.dashboard.slow_down:
                            time.sleep(frame_delay * frame_interval / self.dashboard.speed)

        processing_thread = threading.Thread(target=process_frames)
        processing_thread.daemon = True
        processing_thread.start()

        self.dashboard.run(self.get_current_assignments, self.get_advice, self.get_current_image_path, dir_mode=False, video_mode=True, frame_func=lambda: self.current_frame, recording_toggle_func=lambda start: self.toggle_recording(start), game_mode="rush_n_cash")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='HoPilot Poker Copilot')
    parser.add_argument('--window-title', help='Title of the window to capture')
    parser.add_argument('--replay-video', help='Path to video file to replay')
    args = parser.parse_args()

    if args.replay_video:
        # Create detector for replay mode
        detector = CardDetector()
        analyzer = PokerAnalyzer()
        dashboard = Dashboard()

        # Track current assignments for replay
        replay_state = {'assignments': {}, 'phase': 'pre-flop'}

        def get_replay_assignments():
            return replay_state['assignments'].copy()

        def get_replay_advice():
            hole_cards = []
            if replay_state['assignments'].get('hero_hole_1'):
                hole_cards.append(replay_state['assignments']['hero_hole_1'][0])
            if replay_state['assignments'].get('hero_hole_2'):
                hole_cards.append(replay_state['assignments']['hero_hole_2'][0])

            board_cards = []
            for slot in ['flop_1', 'flop_2', 'flop_3', 'turn', 'river']:
                if replay_state['assignments'].get(slot):
                    board_cards.append(replay_state['assignments'][slot][0])

            return analyzer.get_advice(hole_cards, board_cards, replay_state['phase'])

        def process_replay_frame(frame):
            replay_state['assignments'] = detector.detect_cards(frame)
            board_count = sum(1 for slot in ['flop_1', 'flop_2', 'flop_3', 'turn', 'river'] if replay_state['assignments'].get(slot))
            if board_count == 0:
                replay_state['phase'] = 'pre-flop'
            elif board_count <= 3:
                replay_state['phase'] = 'flop'
            elif board_count == 4:
                replay_state['phase'] = 'turn'
            else:
                replay_state['phase'] = 'river'

        dashboard.run(get_replay_assignments, get_replay_advice, lambda: args.replay_video, dir_mode=False, video_mode=True, frame_func=None, recording_toggle_func=None, replay_mode=True, video_path=args.replay_video, frame_processor=process_replay_frame, game_mode="rush_n_cash")
    else:
        pilot = HoPilot(args.window_title)
        pilot.run_with_capture()