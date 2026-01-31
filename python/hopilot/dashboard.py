import pygame
import sys
import threading
import os
import shutil
import cv2

class Command:
    def execute(self):
        raise NotImplementedError

class TogglePauseCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        with self.dashboard.speed_lock:
            self.dashboard.paused = not self.dashboard.paused
            print(f"Pause toggled: {'Paused' if self.dashboard.paused else 'Playing'}")

class SpeedUpCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        with self.dashboard.speed_lock:
            self.dashboard.speed = min(self.dashboard.speed * 1.5, 10.0)
            self.dashboard.fast_speed = self.dashboard.speed

class SpeedDownCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        with self.dashboard.speed_lock:
            self.dashboard.speed = max(self.dashboard.speed / 1.5, 0.1)
            self.dashboard.fast_speed = self.dashboard.speed

class ToggleSlowCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        with self.dashboard.speed_lock:
            if self.dashboard.replay_mode:
                # In replay, toggle between normal (1.0x) and fast speed
                if self.dashboard.speed == 1.0:
                    self.dashboard.speed = self.dashboard.fast_speed
                else:
                    self.dashboard.speed = 1.0
                print(f"Replay speed toggled to {self.dashboard.speed:.1f}x")
            else:
                # In live, toggle slow_down
                self.dashboard.slow_down = not self.dashboard.slow_down

class ToggleRecordingCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        with self.dashboard.speed_lock:
            self.dashboard.recording = not self.dashboard.recording
            if self.dashboard.recording_toggle_func:
                self.dashboard.recording_toggle_func(self.dashboard.recording)

class ToggleAutoSaveCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        with self.dashboard.speed_lock:
            self.dashboard.auto_save = not self.dashboard.auto_save
            if not self.dashboard.auto_save:
                # Reset states when turning off
                self.dashboard.round_active = False
                self.dashboard.saved_this_round = {i: False for i in range(len(self.dashboard.bboxes))}
            print(f"Auto save toggled: {'ON' if self.dashboard.auto_save else 'OFF'}")

class CropBBoxesCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        frame = None
        if self.dashboard.replay_mode:
            frame = getattr(self.dashboard, 'current_frame', None)
        elif self.dashboard.frame_func:
            frame = self.dashboard.frame_func()
        if frame is not None:
            import os
            os.makedirs('recordings/screenshots', exist_ok=True)
            files = os.listdir('recordings/screenshots')
            bbox_files = [f for f in files if f.startswith('bbox') and f.endswith('.png')]
            numbers = []
            for f in bbox_files:
                try:
                    num = int(f[4:-4])
                    numbers.append(num)
                except ValueError:
                    pass
            next_num = max(numbers) + 1 if numbers else 1
            # Crop boxes using bboxes
            crops = [frame[y1:y2, x1:x2] for x1, y1, x2, y2 in self.dashboard.bboxes]
            for i, crop in enumerate(crops, start=next_num):
                path = f'recordings/screenshots/bbox{i}.png'
                cv2.imwrite(path, crop)
                print(f"Saved {path}")
                next_num += 1

class ScreenshotCommand(Command):
    def __init__(self, dashboard, image_path_func):
        self.dashboard = dashboard
        self.image_path_func = image_path_func

    def execute(self):
        if self.dashboard.replay_mode:
            frame = getattr(self.dashboard, 'current_frame', None)
            if frame is not None:
                screenshots_dir = 'recordings/screenshots'
                os.makedirs(screenshots_dir, exist_ok=True)
                files = os.listdir(screenshots_dir)
                png_files = [f for f in files if f.endswith('.png')]
                numbers = []
                for f in png_files:
                    try:
                        num = int(f[:-4])
                        numbers.append(num)
                    except ValueError:
                        pass
                next_num = max(numbers) + 1 if numbers else 1
                screenshot_path = os.path.join(screenshots_dir, f'{next_num}.png')
                cv2.imwrite(screenshot_path, frame)
                print(f"Screenshot saved to {screenshot_path}")
        else:
            current_image_path = self.image_path_func() if self.image_path_func else None
            if current_image_path and os.path.exists(current_image_path):
                screenshots_dir = 'recordings/screenshots'
                os.makedirs(screenshots_dir, exist_ok=True)
                files = os.listdir(screenshots_dir)
                png_files = [f for f in files if f.endswith('.png')]
                numbers = []
                for f in png_files:
                    try:
                        num = int(f[:-4])
                        numbers.append(num)
                    except ValueError:
                        pass
                next_num = max(numbers) + 1 if numbers else 1
                screenshot_path = os.path.join(screenshots_dir, f'{next_num}.png')
                shutil.copy(current_image_path, screenshot_path)
                print(f"Screenshot saved to {screenshot_path}")

class Dashboard:
    def __init__(self, width=900, height=600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("HoPilot - Poker Hold'em Copilot")
        self.font = pygame.font.SysFont(None, 24)
        self.large_font = pygame.font.SysFont(None, 36)
        self.clock = pygame.time.Clock()
        self.speed = 1.0
        self.slow_down = True
        self.paused = False
        self.speed_lock = threading.Lock()
        self.fast_speed = 1.0
        self.recording = False
        self.bboxes = [
            (68, 416, 84 + 1, 450),   # bbox1
            (123, 416, 139 + 1, 450), # bbox2
            (179, 416, 195 + 1, 450), # bbox3
            (234, 416, 250 + 1, 450), # bbox4
            (289, 416, 305 + 1, 450)  # bbox5
        ]
        self.auto_save = False
        self.round_active = False
        self.saved_this_round = {i: False for i in range(len(self.bboxes))}
        # Suffixes for each bbox: f1, f2, f3, t, r
        self.bbox_suffixes = ['f1', 'f2', 'f3', 't', 'r']
        # Initialize auto save counter
        auto_capture_dir = 'recordings/screenshots/auto_capture'
        os.makedirs(auto_capture_dir, exist_ok=True)
        files = os.listdir(auto_capture_dir)
        png_files = [f for f in files if f.endswith('.png')]
        numbers = []
        for f in png_files:
            parts = f.split('_')
            if parts and parts[0].isdigit():
                try:
                    num = int(parts[0])
                    numbers.append(num)
                except ValueError:
                    pass
        self.auto_save_counter = max(numbers) if numbers else 0

        # Button dimensions
        self.button_width = 100
        self.button_height = 30
        self.button_y = 450
        self.pause_rect = (600, self.button_y, self.button_width, self.button_height)
        self.speed_up_rect = (710, self.button_y, self.button_width, self.button_height)
        self.speed_down_rect = (600, self.button_y + 40, self.button_width, self.button_height)
        self.slow_toggle_rect = (710, self.button_y + 40, self.button_width, self.button_height)
        self.screenshot_rect = (710, self.button_y + 80, self.button_width, self.button_height)
        self.recording_rect = (600, self.button_y + 80, self.button_width, self.button_height)
        self.crop_rect = (600, self.button_y + 120, self.button_width, self.button_height)
        self.prev_rect = (600, self.button_y + 120, self.button_width, self.button_height)
        self.next_rect = (710, self.button_y + 120, self.button_width, self.button_height)
        self.auto_save_rect = (710, self.button_y + 120, self.button_width, self.button_height)

    def is_mouse_inside(self, rect, pos):
        x, y = pos
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    def is_near_white(self, pixel):
        # pixel is (b, g, r) in OpenCV
        b, g, r = pixel
        # Near white if all channels >= 230 (close to 255)
        return r >= 230 and g >= 230 and b >= 230

    def is_bbox_steady(self, frame, bbox):
        x1, y1, x2, y2 = bbox
        corners = [
            (x1, y1),      # upper left
            (x2-1, y1),    # upper right
            (x1, y2-1),    # lower left
            (x2-1, y2-1)   # lower right
        ]
        for x, y in corners:
            if y < 0 or y >= frame.shape[0] or x < 0 or x >= frame.shape[1]:
                return False  # out of bounds
            pixel = frame[y, x]
            if not self.is_near_white(pixel):
                return False
        # Check entire left vertical line
        for y in range(y1, y2):
            pixel = frame[y, x1]
            if not self.is_near_white(pixel):
                return False
        return True

    def check_auto_save(self, frame):
        if not self.auto_save or frame is None:
            return

        # Check bbox1 (index 0) for round detection
        x1, y1, x2, y2 = self.bboxes[0]
        pixel = frame[y1, x1]  # upper left corner
        is_white = self.is_near_white(pixel)

        if is_white and not self.round_active:
            # Start of new round
            self.round_active = True
            self.saved_this_round = {i: False for i in range(len(self.bboxes))}
            print("New round started")
        elif not is_white and self.round_active:
            # Round ended
            self.round_active = False
            print("Round ended")

        if self.round_active:
            # Check each bbox for saving
            for i, bbox in enumerate(self.bboxes):
                if self.saved_this_round[i]:
                    continue
                x1, y1, x2, y2 = bbox
                if self.is_bbox_steady(frame, bbox):
                    # Save the crop
                    crop = frame[y1:y2, x1:x2]
                    os.makedirs('recordings/screenshots/auto_capture', exist_ok=True)
                    suffix = self.bbox_suffixes[i] if i < len(self.bbox_suffixes) else f'bbox{i}'
                    self.auto_save_counter += 1
                    path = f'recordings/screenshots/auto_capture/{self.auto_save_counter}_{suffix}.png'
                    cv2.imwrite(path, crop)
                    print(f"Saved auto capture {path}")
                    self.saved_this_round[i] = True

    def draw_text(self, text, x, y, font=None, color=(255, 255, 255)):
        if font is None:
            font = self.font
        text_surface = font.render(text, True, color)
        self.screen.blit(text_surface, (x, y))

    def display_cards(self, assignments, advice, image_path=None):
        self.screen.fill((0, 0, 0))  # Black background

        # Title
        self.draw_text("HoPilot Dashboard", 50, 20, self.large_font)

        if self.dir_mode and image_path:
            self.draw_text(f"Image: {os.path.basename(image_path)}", 50, 50)

        # Hole cards
        self.draw_text("Hole Cards:", 50, 80)
        hole1 = assignments.get('hero_hole_1')
        hole2 = assignments.get('hero_hole_2')
        if hole1:
            self.draw_text(f"{hole1[0]} (conf: {hole1[1]:.2f})", 50, 110)
        else:
            self.draw_text("Not detected", 50, 110)
        if hole2:
            self.draw_text(f"{hole2[0]} (conf: {hole2[1]:.2f})", 50, 140)
        else:
            self.draw_text("Not detected", 50, 140)

        # Board cards
        self.draw_text("Board Cards:", 50, 200)
        board_slots = ['flop_1', 'flop_2', 'flop_3', 'turn', 'river']
        y = 230
        for slot in board_slots:
            card = assignments.get(slot)
            if card:
                self.draw_text(f"{slot}: {card[0]} (conf: {card[1]:.2f})", 50, y)
            else:
                self.draw_text(f"{slot}: Not detected", 50, y)
            y += 30

        # Advice
        self.draw_text("Advice:", 50, 400, self.large_font)
        self.draw_text(advice, 50, 440)

        # Draw buttons on the right
        if self.video_mode:
            # Pause/Play
            pygame.draw.rect(self.screen, (255,255,0), self.pause_rect)
            text = "Play" if self.paused else "Pause"
            self.screen.blit(self.font.render(text, True, (0,0,0)), (605, self.button_y + 5))

            # Speed up
            pygame.draw.rect(self.screen, (0,255,0), self.speed_up_rect)
            self.screen.blit(self.font.render("Speed +", True, (0,0,0)), (715, self.button_y + 5))

            # Speed down
            pygame.draw.rect(self.screen, (255,0,0), self.speed_down_rect)
            self.screen.blit(self.font.render("Speed -", True, (0,0,0)), (605, self.button_y + 45))

            # Toggle slow / speed toggle
            if self.replay_mode:
                color = (255,0,0) if self.speed == 1.0 else (0,255,0)
                pygame.draw.rect(self.screen, color, self.slow_toggle_rect)
                text = "Normal" if self.speed == 1.0 else "Fast"
                self.screen.blit(self.font.render(text, True, (0,0,0)), (715, self.button_y + 45))
            else:
                color = (0,255,0) if self.slow_down else (255,0,0)
                pygame.draw.rect(self.screen, color, self.slow_toggle_rect)
                text = "Slow ON" if self.slow_down else "Slow OFF"
                self.screen.blit(self.font.render(text, True, (0,0,0)), (715, self.button_y + 45))

            # Speed display
            speed_text = f"Replay Speed: {self.speed:.1f}x" if self.replay_mode else f"Speed: {self.speed:.1f}x"
            self.draw_text(speed_text, 600, self.button_y - 30)

        # Screenshot button
        pygame.draw.rect(self.screen, (0,255,255), self.screenshot_rect)
        self.screen.blit(self.font.render("Screenshot", True, (0,0,0)), (715, self.button_y + 85))

        if self.video_mode:
            # Recording button
            color = (0,255,0) if self.recording else (255,0,0)
            pygame.draw.rect(self.screen, color, self.recording_rect)
            text = "Rec ON" if self.recording else "Rec OFF"
            self.screen.blit(self.font.render(text, True, (0,0,0)), (605, self.button_y + 85))

            # Crop BBoxes button
            pygame.draw.rect(self.screen, (255,255,0), self.crop_rect)
            self.screen.blit(self.font.render("Crop BBoxes", True, (0,0,0)), (605, self.button_y + 125))

            # Auto Save button
            color = (0,255,0) if self.auto_save else (255,0,0)
            pygame.draw.rect(self.screen, color, self.auto_save_rect)
            text = "AutoSave ON" if self.auto_save else "AutoSave OFF"
            self.screen.blit(self.font.render(text, True, (0,0,0)), (715, self.button_y + 125))

        if self.dir_mode:
            # Prev button
            pygame.draw.rect(self.screen, (255,165,0), self.prev_rect)
            self.screen.blit(self.font.render("Prev", True, (0,0,0)), (605, self.button_y + 125))

            # Next button
            pygame.draw.rect(self.screen, (255,165,0), self.next_rect)
            self.screen.blit(self.font.render("Next", True, (0,0,0)), (715, self.button_y + 125))

        pygame.display.flip()

    def show_debug_image(self, image_path):
        if image_path:
            try:
                import cv2
                cv2.imshow("Debug Image", cv2.imread(image_path))
                cv2.waitKey(1)
            except:
                pass

    def run(self, card_assignments_func, advice_func, image_path_func=None, prev_func=None, next_func=None, dir_mode=False, video_mode=False, frame_func=None, recording_toggle_func=None, replay_mode=False, video_path=None):
        self.card_assignments_func = card_assignments_func
        self.advice_func = advice_func
        self.image_path_func = image_path_func
        self.prev_func = prev_func
        self.next_func = next_func
        self.dir_mode = dir_mode
        self.video_mode = video_mode
        self.frame_func = frame_func
        self.recording_toggle_func = recording_toggle_func
        self.replay_mode = replay_mode
        self.video_path = video_path
        if self.replay_mode:
            self.paused = True  # Start paused in replay mode
        if self.replay_mode and self.video_path:
            self.cap = cv2.VideoCapture(self.video_path)
            self.current_frame_idx = 0
            # Read first frame for initial display
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame

        # Create debug window if frame_func is provided or in replay mode
        if self.frame_func or self.replay_mode:
            cv2.namedWindow("Captured Frame", cv2.WINDOW_NORMAL)

        # Create commands
        toggle_pause_cmd = TogglePauseCommand(self)
        speed_up_cmd = SpeedUpCommand(self)
        speed_down_cmd = SpeedDownCommand(self)
        toggle_slow_cmd = ToggleSlowCommand(self)
        toggle_recording_cmd = ToggleRecordingCommand(self)
        toggle_auto_save_cmd = ToggleAutoSaveCommand(self)
        crop_cmd = CropBBoxesCommand(self)
        screenshot_cmd = ScreenshotCommand(self, self.image_path_func)

        running = True
        self.fps = 30
        if self.replay_mode:
            self.fps = 30  # Use 30 FPS for replay
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.video_mode and self.is_mouse_inside(self.pause_rect, event.pos):
                        toggle_pause_cmd.execute()
                    elif self.video_mode and self.is_mouse_inside(self.speed_up_rect, event.pos):
                        speed_up_cmd.execute()
                    elif self.video_mode and self.is_mouse_inside(self.speed_down_rect, event.pos):
                        speed_down_cmd.execute()
                    elif self.video_mode and self.is_mouse_inside(self.slow_toggle_rect, event.pos):
                        toggle_slow_cmd.execute()
                    elif self.is_mouse_inside(self.screenshot_rect, event.pos):
                        screenshot_cmd.execute()
                    elif self.video_mode and self.is_mouse_inside(self.recording_rect, event.pos):
                        toggle_recording_cmd.execute()
                    elif self.video_mode and self.is_mouse_inside(self.crop_rect, event.pos):
                        crop_cmd.execute()
                    elif self.video_mode and self.is_mouse_inside(self.auto_save_rect, event.pos):
                        toggle_auto_save_cmd.execute()
                    elif self.dir_mode and self.is_mouse_inside(self.prev_rect, event.pos) and self.prev_func:
                        self.prev_func()
                    elif self.dir_mode and self.is_mouse_inside(self.next_rect, event.pos) and self.next_func:
                        self.next_func()

            if self.replay_mode:
                if not self.paused:
                    ret, frame = self.cap.read()
                    if not ret:
                        running = False  # Stop when video ends
                        break
                    if ret:
                        self.current_frame = frame
                        self.check_auto_save(frame)
                        frame_copy = frame.copy()
                        # Draw fixed bounding boxes
                        for x1, y1, x2, y2 in self.bboxes:
                            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        assignments = {}
                        advice = "Replaying video"
                        image_path = self.video_path
                        self.display_cards(assignments, advice, image_path)
                        cv2.imshow("Captured Frame", frame_copy)
                        cv2.resizeWindow("Captured Frame", frame.shape[1], frame.shape[0])
                        cv2.waitKey(1)
                        pygame.time.wait(int(1000 / (self.fps * self.speed)))
                else:
                    # When paused, still display the last frame
                    if hasattr(self, 'current_frame') and self.current_frame is not None:
                        frame_copy = self.current_frame.copy()
                        # Draw fixed bounding boxes
                        for x1, y1, x2, y2 in self.bboxes:
                            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        assignments = {}
                        advice = "Replaying video (Paused)"
                        image_path = self.video_path
                        self.display_cards(assignments, advice, image_path)
                        cv2.imshow("Captured Frame", frame_copy)
                        cv2.resizeWindow("Captured Frame", frame.shape[1], frame.shape[0])
                        cv2.waitKey(1)
                    pygame.time.wait(100)
            else:
                # Get current card assignments and advice
                assignments = card_assignments_func()
                advice = advice_func()
                image_path = image_path_func() if image_path_func else None

                self.display_cards(assignments, advice, image_path)
                self.show_debug_image(image_path)

                # Display captured frame in debug window if available
                if self.frame_func:
                    frame = self.frame_func()
                    if frame is not None:
                        self.check_auto_save(frame)
                        frame_copy = frame.copy()
                        assignments = card_assignments_func()
                        for slot, data in assignments.items():
                            if data:
                                name, conf, xyxy = data
                                x1, y1, x2, y2 = xyxy
                                cv2.rectangle(frame_copy, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                                cv2.putText(frame_copy, f"{name} {conf:.2f}", (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        # Draw fixed bounding boxes
                        for x1, y1, x2, y2 in self.bboxes:
                            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        cv2.imshow("Captured Frame", frame_copy)
                        cv2.resizeWindow("Captured Frame", frame.shape[1], frame.shape[0])
                        cv2.waitKey(1)

            self.clock.tick(30)

        pygame.quit()
