import pygame
import sys
import threading
import os
import shutil
import cv2
import numpy as np
import time
from card_layout import CardLayout

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
                self.dashboard.saved_hole_this_round = {i: False for i in range(len(self.dashboard.bboxes_hole))}
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
            # Crop hole boxes using bboxes_hole
            hole_crops = []
            hole_prefixes = ['A', 'B']  # Prefixes for each hole box
            for i, (x1, y1, x2, y2, angle) in enumerate(self.dashboard.bboxes_hole):
                hole_prefix = hole_prefixes[i] if i < len(hole_prefixes) else f'H{i}'
                # Find next number for this hole prefix
                hole_files = [f for f in files if f.startswith(f'hole_{hole_prefix}_') and f.endswith('.png') and not '_orig' in f]
                numbers_hole = []
                for f in hole_files:
                    try:
                        num = int(f[len(f'hole_{hole_prefix}_'):-4])
                        numbers_hole.append(num)
                    except ValueError:
                        pass
                next_hole_num = max(numbers_hole) + 1 if numbers_hole else 1
                center = ((x1 + x2) / 2, (y1 + y2) / 2)
                size = (x2 - x1, y2 - y1)
                rect = (center, size, angle)
                box = cv2.boxPoints(rect)
                x1_bb = int(min(box[:, 0]))
                y1_bb = int(min(box[:, 1]))
                x2_bb = int(max(box[:, 0]))
                y2_bb = int(max(box[:, 1]))
                sub = frame[y1_bb:y2_bb, x1_bb:x2_bb]
                # Save original bounding box crop for debugging
                orig_path = f'recordings/screenshots/hole_{hole_prefix}_{next_hole_num}_orig.png'
                cv2.imwrite(orig_path, sub)
                print(f"Saved {orig_path}")
                rel_center = (center[0] - x1_bb, center[1] - y1_bb)
                M = cv2.getRotationMatrix2D(rel_center, angle, 1.0)
                rotated_sub = cv2.warpAffine(sub, M, (x2_bb - x1_bb, y2_bb - y1_bb))
                crop = rotated_sub[int(rel_center[1] - size[1]/2):int(rel_center[1] + size[1]/2), 
                                   int(rel_center[0] - size[0]/2):int(rel_center[0] + size[0]/2)]
                hole_crops.append(crop)
                # Save the cropped hole
                path = f'recordings/screenshots/hole_{hole_prefix}_{next_hole_num}.png'
                cv2.imwrite(path, crop)
                print(f"Saved {path}")

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
        
        # Initialize later in run() based on game_mode
        self.layout = None
        self.bboxes = []
        self.bboxes_hole = []
        
        self.auto_save = False
        self.round_active = False
        self.saved_this_round = {}
        self.saved_hole_this_round = {}
        # Suffixes for each bbox: f1, f2, f3, t, r
        self.bbox_suffixes = ['f1', 'f2', 'f3', 't', 'r']
        # Suffixes for hole cards
        self.bbox_hole_suffixes = ['hA', 'hB']
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

    def set_game_mode(self, game_mode):
        """Set the game mode and update bounding boxes"""
        self.layout = CardLayout(game_mode)
        self.bboxes = self.layout.get_board_bboxes()
        self.bboxes_hole = self.layout.get_hole_bboxes()
        self.saved_this_round = {i: False for i in range(len(self.bboxes))}
        self.saved_hole_this_round = {i: False for i in range(len(self.bboxes_hole))}
        
        # Re-initialize auto save counter
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

    def is_card_color_present(self, pixel):
        """Check if pixel matches card background colors (more lenient)"""
        b, g, r = pixel
        
        # Red (hearts) - high red, moderate dominance
        is_red = r > 80 and r > g + 20 and r > b + 20
        
        # Blue (diamonds) - high blue, moderate dominance  
        is_blue = b > 80 and b > r + 20 and b > g + 20
        
        # Green (clubs) - high green, moderate dominance
        is_green = g > 80 and g > r + 20 and g > b + 20
        
        # Black/dark (spades) - all channels low
        is_dark = r < 60 and g < 60 and b < 60
        
        # Also include very bright pixels (white text/symbols)
        is_bright = r > 200 and g > 200 and b > 200
        
        return is_red or is_blue or is_green or is_dark or is_bright

    def calculate_image_sharpness(self, image):
        """Calculate image sharpness using Laplacian variance"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def calculate_image_contrast(self, image):
        """Calculate image contrast (standard deviation of grayscale)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return np.std(gray)

    def is_bbox_steady(self, frame, bbox):
        """Improved steady detection using multiple criteria"""
        x1, y1, x2, y2 = bbox
        
        # Extract the card region
        card_crop = frame[y1:y2, x1:x2]
        if card_crop.size == 0:
            return False
        
        # Criterion 1: Sharpness (Laplacian variance)
        # Good cards: > 8000, Bad/transit cards: < 3000
        sharpness = self.calculate_image_sharpness(card_crop)
        is_sharp = sharpness > 5000  # Higher threshold based on analysis
        
        # Criterion 2: Contrast
        # Good cards: > 90, Bad cards: < 30
        contrast = self.calculate_image_contrast(card_crop)
        has_good_contrast = contrast > 60  # Higher threshold
        
        # Criterion 3: Card color presence (more lenient)
        card_color_pixels = 0
        total_pixels = card_crop.shape[0] * card_crop.shape[1]
        
        # Sample pixels more efficiently (every 2nd pixel)
        for y in range(0, card_crop.shape[0], 2):
            for x in range(0, card_crop.shape[1], 2):
                pixel = card_crop[y, x]
                if self.is_card_color_present(pixel):
                    card_color_pixels += 1
        
        sampled_pixels = (card_crop.shape[0] // 2) * (card_crop.shape[1] // 2)
        color_ratio = card_color_pixels / sampled_pixels if sampled_pixels > 0 else 0
        has_card_colors = color_ratio > 0.3  # 30% of sampled pixels
        
        # Criterion 4: Edge density (cards should have some structure)
        gray = cv2.cvtColor(card_crop, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edge_pixels = np.sum(edges > 0)
        edge_ratio = edge_pixels / total_pixels
        has_edges = edge_ratio > 0.02  # At least 2% edges
        
        # Criterion 5: Left vertical line should be solid color (no white pixels)
        # Cards have colored backgrounds, white text/symbols should not be on the left edge
        # THIS IS A HARD RULE - if left edge is not solid, reject immediately
        left_edge_solid = True
        left_column_x = 0  # Leftmost column
        white_threshold = 200  # RGB values above this are considered "white"
        
        for y in range(card_crop.shape[0]):
            pixel = card_crop[y, left_column_x]
            b, g, r = pixel
            # Check if pixel is white/bright (not solid card color)
            if r > white_threshold and g > white_threshold and b > white_threshold:
                left_edge_solid = False
                break
        
        # Hard rule: reject if left edge is not solid
        if not left_edge_solid:
            return False
        
        # Combine remaining criteria with weights
        score = 0
        score += 0.4 if is_sharp else 0
        score += 0.3 if has_good_contrast else 0
        score += 0.2 if has_card_colors else 0
        score += 0.1 if has_edges else 0
        
        # Consider steady if score is high enough
        return score > 0.6

    def check_auto_save(self, frame):
        if not self.auto_save or frame is None:
            return

        # Simplified round detection: check if first flop card (bbox1) is steady
        # In Hold'em, flop appearance signals round start
        flop_bbox = self.bboxes[0]  # First flop card (f1)
        flop_is_steady = self.is_bbox_steady(frame, flop_bbox)

        if flop_is_steady and not self.round_active:
            # Start of new round (flop detected)
            self.round_active = True
            self.saved_this_round = {i: False for i in range(len(self.bboxes))}
            self.saved_hole_this_round = {i: False for i in range(len(self.bboxes_hole))}
            self.round_start_time = time.time()
            print("New round started (flop detected)")
        elif not flop_is_steady and self.round_active:
            # Round ended (flop no longer steady - likely new hand/shuffle)
            self.round_active = False
            print("Round ended")

        # Add timeout mechanism to prevent getting stuck (5 minutes)
        current_time = time.time()
        if self.round_active and hasattr(self, 'round_start_time'):
            round_duration = current_time - self.round_start_time
            if round_duration > 300:  # 5 minutes timeout
                print("Round timeout - resetting auto-save state")
                self.round_active = False
                self.saved_this_round = {i: False for i in range(len(self.bboxes))}
                self.saved_hole_this_round = {i: False for i in range(len(self.bboxes_hole))}

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

            # Check each hole bbox for saving
            for i, (x1, y1, x2, y2, angle) in enumerate(self.bboxes_hole):
                if self.saved_hole_this_round[i]:
                    continue
                # For hole cards, save immediately when round starts (don't wait for steady detection)
                # since hole cards are usually visible throughout the hand
                center = ((x1 + x2) / 2, (y1 + y2) / 2)
                size = (x2 - x1, y2 - y1)
                rect = (center, size, angle)
                box = cv2.boxPoints(rect)
                x1_bb = int(min(box[:, 0]))
                y1_bb = int(min(box[:, 1]))
                x2_bb = int(max(box[:, 0]))
                y2_bb = int(max(box[:, 1]))
                sub = frame[y1_bb:y2_bb, x1_bb:x2_bb]
                if sub.size == 0:
                    continue
                # Apply rotation
                rel_center = (center[0] - x1_bb, center[1] - y1_bb)
                M = cv2.getRotationMatrix2D(rel_center, angle, 1.0)
                rotated_sub = cv2.warpAffine(sub, M, (x2_bb - x1_bb, y2_bb - y1_bb))
                crop = rotated_sub[int(rel_center[1] - size[1]/2):int(rel_center[1] + size[1]/2), 
                                   int(rel_center[0] - size[0]/2):int(rel_center[0] + size[0]/2)]
                if crop.size == 0:
                    continue
                # Save immediately (hole cards are typically visible throughout the hand)
                os.makedirs('recordings/screenshots/auto_capture', exist_ok=True)
                suffix = self.bbox_hole_suffixes[i] if i < len(self.bbox_hole_suffixes) else f'hole{i}'
                self.auto_save_counter += 1
                path = f'recordings/screenshots/auto_capture/{self.auto_save_counter}_{suffix}.png'
                cv2.imwrite(path, crop)
                print(f"Saved auto capture {path}")
                self.saved_hole_this_round[i] = True

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
            name, conf = hole1[0], hole1[1]
            self.draw_text(f"{name} (conf: {conf:.2f})", 50, 110)
        else:
            self.draw_text("Not detected", 50, 110)
        if hole2:
            name, conf = hole2[0], hole2[1]
            self.draw_text(f"{name} (conf: {conf:.2f})", 50, 140)
        else:
            self.draw_text("Not detected", 50, 140)

        # Board cards
        self.draw_text("Board Cards:", 50, 200)
        board_slots = ['flop_1', 'flop_2', 'flop_3', 'turn', 'river']
        y = 230
        for slot in board_slots:
            card = assignments.get(slot)
            if card:
                name, conf = card[0], card[1]
                self.draw_text(f"{slot}: {name} (conf: {conf:.2f})", 50, y)
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

    def run(self, card_assignments_func, advice_func, image_path_func=None, prev_func=None, next_func=None, dir_mode=False, video_mode=False, frame_func=None, recording_toggle_func=None, replay_mode=False, video_path=None, frame_processor=None, game_mode="rush_n_cash"):
        # Set up game mode and bounding boxes
        self.set_game_mode(game_mode)
        
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
        self.frame_processor = frame_processor
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
                        # Process frame for card detection if processor provided
                        if self.frame_processor:
                            self.frame_processor(frame)
                        frame_copy = frame.copy()
                        # Draw fixed bounding boxes
                        for x1, y1, x2, y2 in self.bboxes:
                            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        # Draw hole card bounding boxes in cyan
                        for x1, y1, x2, y2, angle in self.bboxes_hole:
                            center = ((x1 + x2) / 2, (y1 + y2) / 2)
                            size = (x2 - x1, y2 - y1)
                            rect = (center, size, angle)
                            box = cv2.boxPoints(rect)
                            box = box.astype(np.int32)
                            cv2.drawContours(frame_copy, [box], 0, (255, 255, 0), 2)

                        assignments = self.card_assignments_func()
                        advice = self.advice_func()
                        image_path = self.video_path
                        self.display_cards(assignments, advice, image_path)
                        cv2.imshow("Captured Frame", frame_copy)
                        cv2.resizeWindow("Captured Frame", frame.shape[1], frame.shape[0])
                        cv2.waitKey(1)
                        pygame.time.wait(int(1000 / (self.fps * self.speed)))
                else:
                    # When paused, still display the last frame
                    if hasattr(self, 'current_frame') and self.current_frame is not None:
                        # Process frame for card detection if processor provided (even when paused)
                        if self.frame_processor and self.replay_mode:
                            self.frame_processor(self.current_frame)
                        frame_copy = self.current_frame.copy()
                        # Draw fixed bounding boxes
                        for x1, y1, x2, y2 in self.bboxes:
                            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        # Draw hole card bounding boxes in cyan
                        for x1, y1, x2, y2, angle in self.bboxes_hole:
                            center = ((x1 + x2) / 2, (y1 + y2) / 2)
                            size = (x2 - x1, y2 - y1)
                            rect = (center, size, angle)
                            box = cv2.boxPoints(rect)
                            box = box.astype(np.int32)
                            cv2.drawContours(frame_copy, [box], 0, (255, 255, 0), 2)
                        assignments = self.card_assignments_func()
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
                        # Draw hole card bounding boxes in cyan
                        for x1, y1, x2, y2, angle in self.bboxes_hole:
                            center = ((x1 + x2) / 2, (y1 + y2) / 2)
                            size = (x2 - x1, y2 - y1)
                            rect = (center, size, angle)
                            box = cv2.boxPoints(rect)
                            box = box.astype(np.int32)
                            cv2.drawContours(frame_copy, [box], 0, (255, 255, 0), 2)
                        cv2.imshow("Captured Frame", frame_copy)
                        cv2.resizeWindow("Captured Frame", frame.shape[1], frame.shape[0])
                        cv2.waitKey(1)

            self.clock.tick(30)

        pygame.quit()
