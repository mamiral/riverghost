import pygame
import sys
import threading
import os
import shutil

class Command:
    def execute(self):
        raise NotImplementedError

class TogglePauseCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        with self.dashboard.speed_lock:
            self.dashboard.paused = not self.dashboard.paused

class SpeedUpCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        with self.dashboard.speed_lock:
            self.dashboard.speed = min(self.dashboard.speed * 1.5, 10.0)

class SpeedDownCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        with self.dashboard.speed_lock:
            self.dashboard.speed = max(self.dashboard.speed / 1.5, 0.1)

class ToggleSlowCommand(Command):
    def __init__(self, dashboard):
        self.dashboard = dashboard

    def execute(self):
        with self.dashboard.speed_lock:
            self.dashboard.slow_down = not self.dashboard.slow_down

class ScreenshotCommand(Command):
    def __init__(self, dashboard, image_path_func):
        self.dashboard = dashboard
        self.image_path_func = image_path_func

    def execute(self):
        current_image_path = self.image_path_func() if self.image_path_func else None
        if current_image_path and os.path.exists(current_image_path):
            screenshots_dir = 'recordings/screenshots'
            os.makedirs(screenshots_dir, exist_ok=True)
            files = os.listdir(screenshots_dir)
            jpeg_files = [f for f in files if f.endswith('.jpeg')]
            numbers = []
            for f in jpeg_files:
                try:
                    num = int(f[:-5])
                    numbers.append(num)
                except ValueError:
                    pass
            next_num = max(numbers) + 1 if numbers else 1
            screenshot_path = os.path.join(screenshots_dir, f'{next_num}.jpeg')
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

        # Button dimensions
        self.button_width = 100
        self.button_height = 30
        self.button_y = 450
        self.pause_rect = (600, self.button_y, self.button_width, self.button_height)
        self.speed_up_rect = (710, self.button_y, self.button_width, self.button_height)
        self.speed_down_rect = (600, self.button_y + 40, self.button_width, self.button_height)
        self.slow_toggle_rect = (710, self.button_y + 40, self.button_width, self.button_height)
        self.screenshot_rect = (710, self.button_y + 80, self.button_width, self.button_height)
        self.prev_rect = (600, self.button_y + 120, self.button_width, self.button_height)
        self.next_rect = (710, self.button_y + 120, self.button_width, self.button_height)

    def is_mouse_inside(self, rect, pos):
        x, y = pos
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh

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

            # Toggle slow
            color = (0,255,0) if self.slow_down else (255,0,0)
            pygame.draw.rect(self.screen, color, self.slow_toggle_rect)
            text = "Slow ON" if self.slow_down else "Slow OFF"
            self.screen.blit(self.font.render(text, True, (0,0,0)), (715, self.button_y + 45))

            # Speed display
            self.draw_text(f"Speed: {self.speed:.1f}x", 600, self.button_y + 80)

        # Screenshot button
        pygame.draw.rect(self.screen, (0,255,255), self.screenshot_rect)
        self.screen.blit(self.font.render("Screenshot", True, (0,0,0)), (715, self.button_y + 85))

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

    def run(self, card_assignments_func, advice_func, image_path_func=None, prev_func=None, next_func=None, dir_mode=False, video_mode=False):
        self.card_assignments_func = card_assignments_func
        self.advice_func = advice_func
        self.image_path_func = image_path_func
        self.prev_func = prev_func
        self.next_func = next_func
        self.dir_mode = dir_mode
        self.video_mode = video_mode

        # Create commands
        toggle_pause_cmd = TogglePauseCommand(self)
        speed_up_cmd = SpeedUpCommand(self)
        speed_down_cmd = SpeedDownCommand(self)
        toggle_slow_cmd = ToggleSlowCommand(self)
        screenshot_cmd = ScreenshotCommand(self, self.image_path_func)

        running = True
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
                    elif self.dir_mode and self.is_mouse_inside(self.prev_rect, event.pos) and self.prev_func:
                        self.prev_func()
                    elif self.dir_mode and self.is_mouse_inside(self.next_rect, event.pos) and self.next_func:
                        self.next_func()

            # Get current card assignments and advice
            assignments = card_assignments_func()
            advice = advice_func()
            image_path = image_path_func() if image_path_func else None

            self.display_cards(assignments, advice, image_path)
            self.show_debug_image(image_path)

            self.clock.tick(30)  # 30 FPS

        pygame.quit()
