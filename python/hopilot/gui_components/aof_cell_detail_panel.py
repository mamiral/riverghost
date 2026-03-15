import pygame


class AoFCellDetailPanel:
    def __init__(self, x: int, y: int, width: int = 220, height: int = 300):
        self.rect = pygame.Rect(x, y, width, height)

    def set_bounds(self, x: int, y: int, width: int, height: int) -> None:
        self.rect = pygame.Rect(x, y, width, height)

    @staticmethod
    def fallback_message_for_status(status: str) -> str:
        normalized = str(status).upper()
        if normalized == "TIMEOUT":
            return "Computation timed out for this cell."
        if normalized == "ERROR":
            return "An error occurred while computing this cell."
        if normalized == "NO_CONTEST":
            return "No contest for this scenario and hand."
        if normalized == "MISSING":
            return "No cached value for this cell."
        if normalized == "UNSELECTED":
            return "Select a matrix cell to inspect details."
        return "Cell data is unavailable."

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, detail_model: dict | None) -> None:
        pygame.draw.rect(surface, (31, 31, 31), self.rect, border_radius=6)
        pygame.draw.rect(surface, (90, 90, 90), self.rect, 1, border_radius=6)
        title = font.render("Cell Detail", True, (220, 220, 220))
        surface.blit(title, (self.rect.x + 10, self.rect.y + 8))

        if not detail_model or not detail_model.get("selected"):
            empty_msg = self.fallback_message_for_status("UNSELECTED")
            text = font.render(empty_msg, True, (180, 180, 180))
            surface.blit(text, (self.rect.x + 10, self.rect.y + 36))
            return

        hand_key = str(detail_model.get("hand_key", "-"))
        metric = str(detail_model.get("metric", "-"))
        status = str(detail_model.get("status", "MISSING"))
        value = str(detail_model.get("display_value", "-"))
        status_message = detail_model.get("status_message")

        lines = [
            f"Hand: {hand_key}",
            f"Metric: {metric.replace('_', ' ')}",
            f"Status: {status}",
        ]
        if status == "AVAILABLE":
            lines.append(f"Value: {value}")
            
            # Add aggregation metadata if available
            sample_count = detail_model.get("sample_count")
            confidence = detail_model.get("confidence")
            if sample_count is not None:
                lines.append(f"Samples: {sample_count}")
            if confidence is not None:
                lines.append(f"Confidence: {confidence:.1%}")
                
        elif status_message:
            lines.append(str(status_message))

        # Draw text lines
        for idx, line in enumerate(lines):
            text = font.render(line, True, (210, 210, 210))
            surface.blit(text, (self.rect.x + 10, self.rect.y + 36 + idx * 20))

        # Draw confidence indicator if available
        confidence = detail_model.get("confidence")
        if status == "AVAILABLE" and confidence is not None:
            confidence_indicator_y = self.rect.y + 36 + len(lines) * 20 + 5
            self._draw_confidence_indicator(surface, confidence, confidence_indicator_y)

        if status != "AVAILABLE":
            badge_rect = pygame.Rect(self.rect.x + 10, self.rect.y + self.rect.height - 32, self.rect.width - 20, 22)
            pygame.draw.rect(surface, (74, 48, 48), badge_rect, border_radius=4)
            pygame.draw.rect(surface, (130, 84, 84), badge_rect, 1, border_radius=4)
            badge_text = font.render("Fallback view", True, (255, 220, 220))
            surface.blit(badge_text, (badge_rect.x + 6, badge_rect.y + 3))
            return

        metric = str(detail_model.get("metric", ""))
        segments = detail_model.get("segments", [])
        chart_rect = pygame.Rect(self.rect.x + 10, self.rect.y + 122, self.rect.width - 20, self.rect.height - 134)

        if metric == "WIN_LOSE_PROBABILITY":
            self._draw_probability_stack(surface, font, chart_rect, segments)
        else:
            self._draw_scalar_metric(surface, font, chart_rect, segments)

    @staticmethod
    def _draw_probability_stack(
        surface: pygame.Surface,
        font: pygame.font.Font,
        chart_rect: pygame.Rect,
        segments: list[dict],
    ) -> None:
        pygame.draw.rect(surface, (24, 24, 24), chart_rect, border_radius=4)
        pygame.draw.rect(surface, (88, 88, 88), chart_rect, 1, border_radius=4)

        bar_w = 34
        bar_x = chart_rect.x + 12
        bar_rect = pygame.Rect(bar_x, chart_rect.y + 8, bar_w, chart_rect.height - 16)
        total_weight = sum(max(0.0, float(segment.get("weight", 0.0))) for segment in segments)
        if total_weight <= 0:
            total_weight = 1.0

        color_map = {
            "positive": (222, 74, 74),
            "neutral": (194, 172, 86),
            "negative": (75, 131, 196),
        }

        current_bottom = bar_rect.bottom
        # Draw from bottom to keep segment proportions visually stable in compact height.
        for segment in segments:
            weight = max(0.0, float(segment.get("weight", 0.0)))
            h = int((weight / total_weight) * bar_rect.height)
            if h <= 0:
                continue
            current_bottom -= h
            seg_rect = pygame.Rect(bar_rect.x, current_bottom, bar_rect.width, h)
            color_role = str(segment.get("color_role", "neutral"))
            pygame.draw.rect(surface, color_map.get(color_role, (140, 140, 140)), seg_rect)

        label_x = bar_rect.right + 12
        for idx, segment in enumerate(segments):
            label = str(segment.get("label", "?"))
            display = str(segment.get("display", "-"))
            text = font.render(f"{label}: {display}", True, (220, 220, 220))
            surface.blit(text, (label_x, chart_rect.y + 8 + idx * 18))

    @staticmethod
    def _draw_scalar_metric(
        surface: pygame.Surface,
        font: pygame.font.Font,
        chart_rect: pygame.Rect,
        segments: list[dict],
    ) -> None:
        pygame.draw.rect(surface, (24, 24, 24), chart_rect, border_radius=4)
        pygame.draw.rect(surface, (88, 88, 88), chart_rect, 1, border_radius=4)

        if not segments:
            return

        segment = segments[0]
        weight = max(0.0, min(1.0, float(segment.get("weight", 0.0))))
        bar_rect = pygame.Rect(chart_rect.x + 12, chart_rect.y + 8, 34, chart_rect.height - 16)
        fill_h = int(bar_rect.height * weight)
        fill_rect = pygame.Rect(bar_rect.x, bar_rect.bottom - fill_h, bar_rect.width, fill_h)
        pygame.draw.rect(surface, (80, 150, 205), fill_rect)
        pygame.draw.rect(surface, (120, 120, 120), bar_rect, 1)

        display = str(segment.get("display", "-"))
        label = str(segment.get("label", "Value"))
        text = font.render(f"{label}: {display}", True, (220, 220, 220))
        surface.blit(text, (bar_rect.right + 12, chart_rect.y + 10))

    def _draw_confidence_indicator(
        self,
        surface: pygame.Surface,
        confidence: float,
        y: int,
    ) -> None:
        """Draw a visual confidence indicator bar."""
        bar_width = 80
        bar_height = 8
        bar_x = self.rect.x + 10
        bar_rect = pygame.Rect(bar_x, y, bar_width, bar_height)
        
        # Background
        pygame.draw.rect(surface, (60, 60, 60), bar_rect, border_radius=2)
        
        # Fill based on confidence level
        fill_width = int(bar_width * confidence)
        if fill_width > 0:
            fill_rect = pygame.Rect(bar_x, y, fill_width, bar_height)
            # Color coding: red (< 0.5), yellow (0.5-0.8), green (> 0.8)
            if confidence < 0.5:
                color = (205, 92, 92)  # Red
            elif confidence < 0.8:
                color = (205, 205, 92)  # Yellow
            else:
                color = (92, 205, 92)  # Green
            pygame.draw.rect(surface, color, fill_rect, border_radius=2)
        
        # Border
        pygame.draw.rect(surface, (120, 120, 120), bar_rect, 1, border_radius=2)