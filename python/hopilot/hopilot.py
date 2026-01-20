import cv2
import time
import threading
from card_detector import CardDetector
from poker_analyzer import PokerAnalyzer
from dashboard import Dashboard

class HoPilot:
    def __init__(self, video_path=None, image_path=None):
        self.detector = CardDetector()
        self.analyzer = PokerAnalyzer()
        self.dashboard = Dashboard()
        self.video_path = video_path
        self.image_path = image_path
        self.current_assignments = {}
        self.phase = 'pre-flop'  # Default phase
        self.lock = threading.Lock()

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

    def process_image(self, image_path):
        assignments = self.detector.detect_cards(image_path)
        with self.lock:
            self.current_assignments = assignments
            self.phase = self.determine_phase(self.current_assignments)
            self.current_image_path = image_path

    def process_video_frame(self, frame):
        # Save frame to temp file or process directly
        # For simplicity, assume frame is path
        self.process_image(frame)

    def run_with_image(self):
        if self.image_path:
            self.process_image(self.image_path)
            self.dashboard.run(self.get_current_assignments, self.get_advice, self.get_current_image_path)

    def run_with_video(self):
        if not self.video_path:
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print("Error opening video file")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_delay = 1.0 / fps if fps > 0 else 0.033  # Default ~30fps

        # Process frames at a reasonable rate, skip some for speed
        frame_interval = 5

        def process_frames():
            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                if frame_count % frame_interval == 0:
                    # Process frame
                    temp_path = 'temp_frame.jpg'
                    cv2.imwrite(temp_path, frame)
                    self.process_image(temp_path)
                    print(f"Processed frame {frame_count}")

            cap.release()
            cv2.destroyAllWindows()

        # Start processing thread
        processing_thread = threading.Thread(target=process_frames)
        processing_thread.daemon = True
        processing_thread.start()

        # Run dashboard concurrently
        self.dashboard.run(self.get_current_assignments, self.get_advice, self.get_current_image_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='HoPilot Poker Copilot')
    parser.add_argument('--image', help='Path to image file')
    parser.add_argument('--video', help='Path to video file')
    args = parser.parse_args()

    if args.video:
        pilot = HoPilot(video_path=args.video)
        pilot.run_with_video()
    elif args.image:
        pilot = HoPilot(image_path=args.image)
        pilot.run_with_image()
    else:
        print("Usage: python hopilot.py --image <path> or --video <path>")