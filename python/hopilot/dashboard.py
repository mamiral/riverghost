import pygame
import sys

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

        pygame.display.flip()

    def show_debug_image(self, image_path):
        if image_path:
            try:
                import cv2
                frame = cv2.imread(image_path)
                if frame is not None:
                    cv2.imshow("Debug Image", frame)
                    cv2.waitKey(1)
            except:
                pass

    def run(self, card_assignments_func, advice_func, image_path_func=None):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Get current card assignments and advice
            assignments = card_assignments_func()
            advice = advice_func()
            image_path = image_path_func() if image_path_func else None

            print(f"Dashboard updating: assignments keys: {list(assignments.keys())}, advice: {advice[:50] if advice else 'None'}")
            self.display_cards(assignments, advice)
            self.show_debug_image(image_path)

            self.clock.tick(30)  # 30 FPS

        pygame.quit()