import cv2
import time
import threading
from card_detector import CardDetector
from poker_analyzer import PokerAnalyzer
from dashboard import Dashboard

class HoPilot:
    def __init__(self, video_path=None, image_path=None, dir_path=None, start_frame=0):
        self.detector = CardDetector()
        self.analyzer = PokerAnalyzer()
        self.dashboard = Dashboard()
        self.video_path = video_path
        self.image_path = image_path
        self.dir_path = dir_path
        self.start_frame = start_frame
        self.current_assignments = {}
        self.phase = 'pre-flop'  # Default phase
        self.lock = threading.Lock()
        self.image_list = []
        self.current_index = 0
        if self.dir_path:
            self.load_image_list()

    def load_image_list(self):
        import os
        import glob
        if not os.path.isdir(self.dir_path):
            raise ValueError(f"Directory {self.dir_path} does not exist")
        # Support common image formats
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif']
        self.image_list = []
        for ext in extensions:
            self.image_list.extend(glob.glob(os.path.join(self.dir_path, ext)))
        self.image_list.sort()  # Sort alphabetically
        if not self.image_list:
            raise ValueError(f"No image files found in {self.dir_path}")

    def prev_image(self):
        if self.image_list:
            self.current_index = (self.current_index - 1) % len(self.image_list)
            self.process_image(self.image_list[self.current_index])

    def next_image(self):
        if self.image_list:
            self.current_index = (self.current_index + 1) % len(self.image_list)
            self.process_image(self.image_list[self.current_index])

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
            self.dashboard.run(self.get_current_assignments, self.get_advice, self.get_current_image_path, dir_mode=False)

    def run_with_dir(self):
        if self.image_list:
            self.process_image(self.image_list[0])  # Start with first image
            self.dashboard.run(self.get_current_assignments, self.get_advice, self.get_current_image_path,
                               prev_func=self.prev_image, next_func=self.next_image, dir_mode=True)

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
            if self.start_frame > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
            frame_count = self.start_frame
            while cap.isOpened():
                with self.dashboard.speed_lock:
                    if self.dashboard.paused:
                        time.sleep(0.1)
                        continue

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

                    # Sleep if slow down enabled
                    with self.dashboard.speed_lock:
                        if self.dashboard.slow_down:
                            time.sleep(frame_delay * frame_interval / self.dashboard.speed)

            cap.release()
            cv2.destroyAllWindows()

        # Start processing thread
        processing_thread = threading.Thread(target=process_frames)
        processing_thread.daemon = True
        processing_thread.start()

        # Run dashboard concurrently
        self.dashboard.run(self.get_current_assignments, self.get_advice, self.get_current_image_path, dir_mode=False, video_mode=True)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='HoPilot Poker Copilot')
    parser.add_argument('--image', help='Path to image file')
    parser.add_argument('--video', help='Path to video file')
    parser.add_argument('--dir', help='Path to directory with images')
    parser.add_argument('--start-frame', type=int, default=0, help='Frame number to start processing from (for video)')
    args = parser.parse_args()

    if args.video:
        pilot = HoPilot(video_path=args.video, start_frame=args.start_frame)
        pilot.run_with_video()
    elif args.image:
        pilot = HoPilot(image_path=args.image)
        pilot.run_with_image()
    elif args.dir:
        pilot = HoPilot(dir_path=args.dir)
        pilot.run_with_dir()
    else:
        print("Usage: python hopilot.py --image <path> or --video <path> or --dir <path> [--start-frame <num>]")