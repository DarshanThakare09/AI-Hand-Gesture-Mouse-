"""
AI Hand Gesture Mouse - Futuristic Head-Up Display (HUD)
Draws modern cyberpunk overlays, glowing active bounding boxes, telemetry meters,
status badges, and gesture quick-guides.
"""
import cv2
import numpy as np
import config

class UIHud:
    def __init__(self):
        self.show_guide = True
        self.ripples = []

    def toggle_guide(self):
        self.show_guide = not self.show_guide
        return self.show_guide

    def add_ripple(self, pt, color=(50, 255, 50)):
        """Spawns an expanding animated sci-fi click ring."""
        if pt and len(pt) == 2:
            self.ripples.append({
                "pt": (int(pt[0]), int(pt[1])),
                "r": 6,
                "max_r": 38,
                "color": color,
                "alpha": 0.95
            })

    def draw_ripples(self, frame):
        """Animates active click ripple shockwaves."""
        if not self.ripples:
            return
        new_ripples = []
        for rip in self.ripples:
            rip["r"] += 4
            rip["alpha"] -= 0.10
            if rip["r"] <= rip["max_r"] and rip["alpha"] > 0.05:
                overlay = frame.copy()
                cv2.circle(overlay, rip["pt"], int(rip["r"]), rip["color"], 2, cv2.LINE_AA)
                cv2.addWeighted(overlay, rip["alpha"], frame, 1.0 - rip["alpha"], 0, frame)
                new_ripples.append(rip)
        self.ripples = new_ripples

    def draw_corner_rect(self, img, pt1, pt2, color, thickness=2, corner_len=20):
        """Draws a sleek tech bounding box with highlighted sci-fi corner brackets."""
        x1, y1 = pt1
        x2, y2 = pt2
        
        # Faint dashed or solid main border
        cv2.rectangle(img, (x1, y1), (x2, y2), (60, 60, 70), 1, cv2.LINE_AA)

        # Top-Left corner
        cv2.line(img, (x1, y1), (x1 + corner_len, y1), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x1, y1), (x1, y1 + corner_len), color, thickness, cv2.LINE_AA)

        # Top-Right corner
        cv2.line(img, (x2, y1), (x2 - corner_len, y1), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x2, y1), (x2, y1 + corner_len), color, thickness, cv2.LINE_AA)

        # Bottom-Left corner
        cv2.line(img, (x1, y2), (x1 + corner_len, y2), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x1, y2), (x1, y2 - corner_len), color, thickness, cv2.LINE_AA)

        # Bottom-Right corner
        cv2.line(img, (x2, y2), (x2 - corner_len, y2), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x2, y2), (x2, y2 - corner_len), color, thickness, cv2.LINE_AA)

    def draw_active_zone(self, frame):
        """Draws the interaction frame margin mapped to screen resolution."""
        x1 = config.FRAME_MARGIN_X
        y1 = config.FRAME_MARGIN_Y
        x2 = config.CAM_WIDTH - config.FRAME_MARGIN_X
        y2 = config.CAM_HEIGHT - config.FRAME_MARGIN_Y

        # Subtle dark mask for non-active periphery
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (config.CAM_WIDTH, y1), (10, 10, 15), -1)
        cv2.rectangle(overlay, (0, y2), (config.CAM_WIDTH, config.CAM_HEIGHT), (10, 10, 15), -1)
        cv2.rectangle(overlay, (0, y1), (x1, y2), (10, 10, 15), -1)
        cv2.rectangle(overlay, (x2, y1), (config.CAM_WIDTH, y2), (10, 10, 15), -1)
        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

        # Draw stylish cyber corners
        self.draw_corner_rect(frame, (x1, y1), (x2, y2), config.THEME["box_border"], thickness=3, corner_len=24)
        
        # Zone label
        cv2.putText(frame, "ACTIVE INTERACTION ZONE", (x1 + 8, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 220, 255), 1, cv2.LINE_AA)

    def draw_header(self, frame, state_str, fps, handedness="Right", feedback=None):
        """Draws top glassmorphism status pill with real-time FPS and mode badge."""
        w = config.CAM_WIDTH

        # Top dark bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 48), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        cv2.line(frame, (0, 48), (w, 48), (50, 50, 65), 1)

        # App Title
        cv2.putText(frame, "AI VIRTUAL MOUSE", (14, 30),
                    cv2.FONT_HERSHEY_DUPLEX, 0.60, (255, 255, 255), 1, cv2.LINE_AA)

        # State color selection
        state_colors = {
            "MOVING": (255, 191, 0),          # Cyan
            "LEFT CLICK": (50, 205, 50),      # Green
            "DOUBLE CLICK": (0, 255, 128),    # Bright Mint
            "RIGHT CLICK": (0, 140, 255),     # Orange
            "DRAGGING": (255, 0, 180),        # Magenta
            "SCROLLING": (230, 216, 173),     # Soft Sky
            "PAUSED": (70, 70, 245),          # Red
            "IDLE (PALM OPEN)": (160, 160, 160),
            "LOCKED (FIST)": (120, 120, 120),
        }
        badge_color = state_colors.get(state_str, (200, 200, 200))

        # State Badge Box
        badge_x = 205
        badge_w = 160
        cv2.rectangle(frame, (badge_x, 10), (badge_x + badge_w, 38), badge_color, 1, cv2.LINE_AA)
        
        # State text centered in badge
        text_size = cv2.getTextSize(state_str, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
        text_x = badge_x + (badge_w - text_size[0]) // 2
        cv2.putText(frame, state_str, (text_x, 29),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, badge_color, 1, cv2.LINE_AA)

        # Handedness badge
        cv2.putText(frame, f"[{handedness}]", (badge_x + badge_w + 10, 29),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 180, 200), 1, cv2.LINE_AA)

        # Audio status indicator
        audio_on = feedback.get("audio_enabled", False) if feedback else False
        snd_text = "SND:ON" if audio_on else "SND:OFF"
        snd_color = (50, 205, 50) if audio_on else (120, 120, 130)
        cv2.putText(frame, snd_text, (badge_x + badge_w + 75, 29),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, snd_color, 1, cv2.LINE_AA)

        # FPS indicator
        fps_color = (50, 205, 50) if fps >= 24 else (0, 165, 255)
        fps_text = f"FPS: {int(fps)}"
        cv2.putText(frame, fps_text, (w - 100, 30),
                    cv2.FONT_HERSHEY_DUPLEX, 0.55, fps_color, 1, cv2.LINE_AA)

    def draw_pinch_meter(self, frame, feedback):
        """Draws visual feedback gauge for index finger pinch distance."""
        dist = feedback.get("index_pinch_dist", 100)
        thresh = config.CLICK_THRESHOLD
        
        bar_x = 14
        bar_y = config.CAM_HEIGHT - 24
        bar_w = 120
        bar_h = 10

        # Progress calculation (clamped 0 to 1)
        # Closer distance = fuller bar
        progress = max(0.0, min(1.0, 1.0 - (dist / 80.0)))
        fill_w = int(progress * bar_w)

        # Bar background
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (35, 35, 45), -1)
        
        # Bar fill (Green when pinch threshold reached, Cyan otherwise)
        fill_color = config.THEME["accent"] if dist <= thresh else config.THEME["primary"]
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), fill_color, -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (100, 100, 120), 1)

        cv2.putText(frame, f"Pinch: {int(dist)}px", (bar_x, bar_y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1, cv2.LINE_AA)

    def draw_telemetry(self, frame, feedback):
        """Draws telemetry information at bottom of screen."""
        h = config.CAM_HEIGHT
        w = config.CAM_WIDTH

        # Description of active state
        desc = feedback.get("active_mode_desc", "")
        if desc:
            cv2.putText(frame, desc, (155, h - 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (230, 230, 240), 1, cv2.LINE_AA)

        # Cursor Screen Position
        cur_pos = feedback.get("cursor_pos", (0, 0))
        pos_text = f"X: {cur_pos[0]}  Y: {cur_pos[1]}"
        cv2.putText(frame, pos_text, (w - 145, h - 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 200, 255), 1, cv2.LINE_AA)

    def draw_gesture_guide(self, frame):
        """Draws interactive on-screen quick reference cheat sheet."""
        if not self.show_guide:
            cv2.putText(frame, "Press 'H' for Gesture Guide", (config.CAM_WIDTH - 200, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (150, 150, 160), 1, cv2.LINE_AA)
            return

        guide_w = 210
        guide_h = 160
        x = config.CAM_WIDTH - guide_w - 12
        y = 56

        # Translucent background card
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + guide_w, y + guide_h), (12, 12, 18), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        cv2.rectangle(frame, (x, y), (x + guide_w, y + guide_h), (50, 50, 65), 1, cv2.LINE_AA)

        # Title
        cv2.putText(frame, "GESTURE MANUAL", (x + 10, y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, config.THEME["primary"], 1, cv2.LINE_AA)
        cv2.line(frame, (x + 10, y + 25), (x + guide_w - 10, y + 25), (45, 45, 55), 1)

        # Gestures List
        gestures = [
            ("Index Up", "Move Cursor"),
            ("Thumb+Index Pinch", "Left Click"),
            ("Hold Pinch >0.3s", "Drag & Drop"),
            ("Quick Double Pinch", "Double Click"),
            ("Index+Middle Up", "Scroll Up/Down"),
            ("Thumb+Middle Pinch", "Right Click"),
            ("Open Palm / Fist", "Idle / Lock"),
        ]

        row_y = y + 42
        for key, act in gestures:
            cv2.putText(frame, key, (x + 10, row_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1, cv2.LINE_AA)
            cv2.putText(frame, act, (x + 120, row_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 220, 150), 1, cv2.LINE_AA)
            row_y += 16

        cv2.putText(frame, "[H] Guide | [S] Audio | [M] Pause | [Q] Quit", (x + 4, y + guide_h - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, (140, 140, 150), 1, cv2.LINE_AA)

    def render(self, frame, feedback, fps, handedness="Right"):
        """Renders complete HUD layer onto the frame."""
        self.draw_active_zone(frame)
        self.draw_header(frame, feedback.get("state", "IDLE"), fps, handedness, feedback=feedback)
        self.draw_pinch_meter(frame, feedback)
        self.draw_telemetry(frame, feedback)
        self.draw_gesture_guide(frame)

        # Check for click shockwave events to animate
        event = feedback.get("event")
        evt_pt = feedback.get("event_point")
        if event and evt_pt:
            if event == "left_click":
                self.add_ripple(evt_pt, config.THEME["accent"])
            elif event == "double_click":
                self.add_ripple(evt_pt, (0, 255, 255))
            elif event == "right_click":
                self.add_ripple(evt_pt, config.THEME["warning"])

        # Render shockwaves
        self.draw_ripples(frame)
