import pygame
import sys
import threading
import os

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

    def draw_text(self, text, x, y, font=None, color=(255, 255, 255)):
        if font is None:
            font = self.font
        text_surface = font.render(text, True, color)
        self.screen.blit(text_surface, (x, y))

    def display_cards(self, assignments, advice):
        self.screen.fill((0, 0, 0))  # Black background

        # Title
        self.draw_text("HoPilot Dashboard", 50, 20, self.large_font)

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
        button_y = 450
        button_width = 100
        button_height = 30

        # Pause/Play
        pygame.draw.rect(self.screen, (255,255,0), (600, button_y, button_width, button_height))
        text = "Play" if self.paused else "Pause"
        self.screen.blit(self.font.render(text, True, (0,0,0)), (605, button_y + 5))

        # Speed up
        pygame.draw.rect(self.screen, (0,255,0), (710, button_y, button_width, button_height))
        self.screen.blit(self.font.render("Speed +", True, (0,0,0)), (715, button_y + 5))

        # Speed down
        pygame.draw.rect(self.screen, (255,0,0), (600, button_y + 40, button_width, button_height))
        self.screen.blit(self.font.render("Speed -", True, (0,0,0)), (605, button_y + 45))

        # Toggle slow
        color = (0,255,0) if self.slow_down else (255,0,0)
        pygame.draw.rect(self.screen, color, (710, button_y + 40, button_width, button_height))
        text = "Slow ON" if self.slow_down else "Slow OFF"
        self.screen.blit(self.font.render(text, True, (0,0,0)), (715, button_y + 45))

        # Speed display
        self.draw_text(f"Speed: {self.speed:.1f}x", 600, button_y + 80)

        pygame.display.flip()

    def show_debug_image(self, image_path):
        if image_path:
            try:
                import cv2
                cv2.imshow("Debug Image", cv2.imread(image_path))
                cv2.waitKey(1)
            except:
                pass

    def run(self, card_assignments_func, advice_func, image_path_func=None):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    button_y = 450
                    if 600 <= x <= 700 and button_y <= y <= button_y + 30:
                        with self.speed_lock:
                            self.paused = not self.paused
                    elif 710 <= x <= 810 and button_y <= y <= button_y + 30:
                        with self.speed_lock:
                            self.speed = min(self.speed * 1.5, 10.0)
                    elif 600 <= x <= 700 and button_y + 40 <= y <= button_y + 70:
                        with self.speed_lock:
                            self.speed = max(self.speed / 1.5, 0.1)
                    elif 710 <= x <= 810 and button_y + 40 <= y <= button_y + 70:
                        with self.speed_lock:
                            self.slow_down = not self.slow_down

            # Get current card assignments and advice
            assignments = card_assignments_func()
            advice = advice_func()
            image_path = image_path_func() if image_path_func else None

            self.display_cards(assignments, advice)
            self.show_debug_image(image_path)

            self.clock.tick(30)  # 30 FPS

        pygame.quit()
