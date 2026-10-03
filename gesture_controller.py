"""
AI Hand Gesture Mouse - Gesture Controller Engine
Translates hand landmarks and finger configurations into OS mouse events
with adaptive smoothing, deadzone filtering, drag-and-drop, and scroll physics.
"""
import time
import math
import numpy as np
import pyautogui
import config

# Initialize PyAutoGUI for real-time responsiveness
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

class GestureController:
    # Gesture States
    STATE_IDLE = "IDLE"
    STATE_MOVE = "MOVING"
    STATE_LEFT_CLICK = "LEFT CLICK"
    STATE_RIGHT_CLICK = "RIGHT CLICK"
    STATE_DOUBLE_CLICK = "DOUBLE CLICK"
    STATE_DRAG = "DRAGGING"
    STATE_SCROLL = "SCROLLING"
    STATE_PAUSED = "PAUSED"

    def __init__(self):
        self.screen_w = config.SCREEN_WIDTH
        self.screen_h = config.SCREEN_HEIGHT
        
        # Cursor position tracking & smoothing
        self.prev_x = self.screen_w // 2
        self.prev_y = self.screen_h // 2
        self.curr_x = self.prev_x
        self.curr_y = self.prev_y
        
        # Click stabilization anchor
        self.anchor_x = self.prev_x
        self.anchor_y = self.prev_y
        
        # State tracking
        self.current_state = self.STATE_IDLE
        self.is_paused = False
        self.is_dragging = False
        self.audio_enabled = getattr(config, "ENABLE_AUDIO_FEEDBACK", False)
        
        # Timestamps for gesture debounce and click detection
        self.pinch_start_time = 0.0
        self.last_click_time = 0.0
        self.last_right_click_time = 0.0
        self.last_scroll_time = 0.0
        
        # Pinch states
        self.is_index_pinched = False
        self.is_middle_pinched = False
        
        # Scroll tracking (relative trackpad mode)
        self.scroll_prev_y = None

    def toggle_pause(self):
        """Toggles between paused and active mouse tracking."""
        self.is_paused = not self.is_paused
        if self.is_paused and self.is_dragging:
            pyautogui.mouseUp(button='left')
            self.is_dragging = False
        return self.is_paused

    def toggle_audio(self):
        """Toggles audio feedback sound on clicks."""
        self.audio_enabled = not self.audio_enabled
        if self.audio_enabled:
            self._play_feedback_sound(1000, 30)
        return self.audio_enabled

    def _play_feedback_sound(self, frequency=1200, duration=25):
        """Plays a non-blocking subtle UI feedback beep."""
        if not self.audio_enabled:
            return
        try:
            import winsound
            import threading
            threading.Thread(target=winsound.Beep, args=(frequency, duration), daemon=True).start()
        except Exception:
            pass

    def _map_coordinates(self, x, y):
        """
        Maps camera coordinates from the active frame margin box
        to the full operating system screen resolution.
        """
        x_min = config.FRAME_MARGIN_X
        x_max = config.CAM_WIDTH - config.FRAME_MARGIN_X
        y_min = config.FRAME_MARGIN_Y
        y_max = config.CAM_HEIGHT - config.FRAME_MARGIN_Y

        # Linear interpolation
        target_x = np.interp(x, (x_min, x_max), (0, self.screen_w))
        target_y = np.interp(y, (y_min, y_max), (0, self.screen_h))

        # Clamp safely within screen boundaries
        target_x = max(0, min(self.screen_w - 1, target_x))
        target_y = max(0, min(self.screen_h - 1, target_y))

        return target_x, target_y

    def _apply_adaptive_smoothing(self, target_x, target_y):
        """
        Dynamically adjusts smoothing factor based on velocity.
        - High smoothing at low velocities -> eliminates human hand micro-tremor.
        - Low smoothing at high velocities -> responsive cursor without perceptible lag.
        """
        delta_x = target_x - self.prev_x
        delta_y = target_y - self.prev_y
        distance = math.hypot(delta_x, delta_y)

        # Tremor deadzone: suppress micro movements
        if distance < config.DEADZONE_PIXELS:
            return self.prev_x, self.prev_y

        # Dynamic smoothing factor interpolation
        smoothing = np.interp(
            distance,
            [15.0, 150.0],
            [config.MAX_SMOOTHING, config.MIN_SMOOTHING]
        )

        curr_x = self.prev_x + (target_x - self.prev_x) / smoothing
        curr_y = self.prev_y + (target_y - self.prev_y) / smoothing

        self.prev_x, self.prev_y = curr_x, curr_y
        return curr_x, curr_y

    def process(self, hand_tracker, landmarks):
        """
        Main gesture decision loop for a single detected hand.
        landmarks: list of 21 landmark dictionaries with keys {'id', 'x', 'y', ...}
        Returns:
            dict containing state, info, and visual feedback metadata.
        """
        now = time.time()
        feedback = {
            "state": self.STATE_PAUSED if self.is_paused else self.STATE_IDLE,
            "cursor_pos": (int(self.prev_x), int(self.prev_y)),
            "index_pinch_dist": 0.0,
            "middle_pinch_dist": 0.0,
            "is_pinched": False,
            "is_dragging": self.is_dragging,
            "active_mode_desc": "",
            "event": None,
            "event_point": None,
            "audio_enabled": self.audio_enabled
        }

        if self.is_paused or not landmarks:
            return feedback

        fingers = hand_tracker.get_fingers_up(landmarks)
        # fingers: [Thumb, Index, Middle, Ring, Pinky]

        # Calculate distances and palm scale for camera-distance invariance
        dist_index_thumb, _, _, _ = hand_tracker.get_distance(4, 8, landmarks)
        dist_middle_thumb, _, _, _ = hand_tracker.get_distance(4, 12, landmarks)
        palm_scale = hand_tracker.get_palm_scale(landmarks)
        
        # Scale normalization (relative to standard ~95px palm at nominal distance)
        scale_ratio = 95.0 / palm_scale
        eff_dist_index = dist_index_thumb * scale_ratio
        eff_dist_middle = dist_middle_thumb * scale_ratio

        feedback["index_pinch_dist"] = eff_dist_index
        feedback["middle_pinch_dist"] = eff_dist_middle

        # Evaluate pinch states with hysteresis buffers
        idx_thresh = config.CLICK_THRESHOLD + (config.PINCH_RELEASE_BUFFER if self.is_index_pinched else 0)
        is_index_pinch = (eff_dist_index < idx_thresh)

        mid_thresh = config.RIGHT_CLICK_THRESHOLD + (config.PINCH_RELEASE_BUFFER if self.is_middle_pinched else 0)
        is_middle_pinch = (eff_dist_middle < mid_thresh) and (eff_dist_index > config.CLICK_THRESHOLD + 12)

        # ------------------------------------------------------------------
        # 1. STANDBY / IDLE GESTURES (Open Palm or Fist)
        # ------------------------------------------------------------------
        if fingers == [1, 1, 1, 1, 1] and not is_index_pinch:
            if self.is_dragging:
                pyautogui.mouseUp(button='left')
                self.is_dragging = False
            self.current_state = self.STATE_IDLE
            feedback["state"] = "IDLE (PALM OPEN)"
            feedback["active_mode_desc"] = "Hand open: Mouse hovering neutral"
            self.scroll_prev_y = None
            return feedback

        if fingers == [0, 0, 0, 0, 0] and not is_index_pinch:
            if self.is_dragging:
                pyautogui.mouseUp(button='left')
                self.is_dragging = False
            self.current_state = self.STATE_IDLE
            feedback["state"] = "LOCKED (FIST)"
            feedback["active_mode_desc"] = "Fist closed: Cursor locked"
            self.scroll_prev_y = None
            return feedback

        # ------------------------------------------------------------------
        # 2. SCROLLING MODE (Index + Middle UP, Ring + Pinky DOWN)
        # ------------------------------------------------------------------
        if fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 0 and fingers[4] == 0 and not is_index_pinch:
            if self.is_dragging:
                pyautogui.mouseUp(button='left')
                self.is_dragging = False

            mid_finger_y = (landmarks[8]["y"] + landmarks[12]["y"]) // 2
            
            if self.scroll_prev_y is None:
                self.scroll_prev_y = mid_finger_y

            delta_y = self.scroll_prev_y - mid_finger_y
            
            # Deadzone prevents scroll jitter when resting
            if abs(delta_y) > 4:
                if now - self.last_scroll_time > config.SCROLL_COOLDOWN:
                    scroll_amount = int(delta_y * config.SCROLL_SPEED_MULTIPLIER)
                    pyautogui.scroll(scroll_amount)
                    self.last_scroll_time = now
                    self.scroll_prev_y = mid_finger_y
            else:
                self.scroll_prev_y = int(0.7 * self.scroll_prev_y + 0.3 * mid_finger_y)
            
            self.current_state = self.STATE_SCROLL
            direction = "UP" if delta_y > 0 else "DOWN"
            feedback["state"] = self.STATE_SCROLL
            feedback["active_mode_desc"] = f"Trackpad Scroll {direction} (Speed: {int(abs(delta_y))})"
            return feedback
        else:
            self.scroll_prev_y = None

        # ------------------------------------------------------------------
        # 3. RIGHT CLICK GESTURE (Thumb + Middle Finger Pinch)
        # ------------------------------------------------------------------
        if is_middle_pinch:
            self.is_middle_pinched = True
            if now - self.last_right_click_time > config.CLICK_COOLDOWN + 0.15:
                pyautogui.rightClick()
                self._play_feedback_sound(1400, 30)
                self.last_right_click_time = now
                self.current_state = self.STATE_RIGHT_CLICK
                feedback["event"] = "right_click"
                feedback["event_point"] = (landmarks[12]["x"], landmarks[12]["y"])
            
            feedback["state"] = self.STATE_RIGHT_CLICK
            feedback["active_mode_desc"] = "Right Click Triggered!"
            return feedback
        else:
            self.is_middle_pinched = False

        # ------------------------------------------------------------------
        # 4. CURSOR MOVEMENT & LEFT CLICK / DRAG (Index Finger Extended or Pinched)
        # ------------------------------------------------------------------
        if fingers[1] == 1 or is_index_pinch or self.is_index_pinched or self.is_dragging:
            index_x, index_y = landmarks[8]["x"], landmarks[8]["y"]
            target_x, target_y = self._map_coordinates(index_x, index_y)

            feedback["is_pinched"] = is_index_pinch

            if is_index_pinch:
                if not self.is_index_pinched:
                    # Pinch just initiated -> Anchor cursor to prevent click-slip jerk
                    self.is_index_pinched = True
                    self.pinch_start_time = now
                    self.anchor_x, self.anchor_y = self.prev_x, self.prev_y
                else:
                    pinch_duration = now - self.pinch_start_time
                    if pinch_duration > config.DRAG_HOLD_DELAY and not self.is_dragging:
                        # Hold delay exceeded -> Engage Drag Mode
                        pyautogui.mouseDown(button='left')
                        self.is_dragging = True
                        self._play_feedback_sound(800, 40)

                # Cursor positioning:
                if self.is_dragging:
                    # During drag, cursor tracks hand movement
                    curr_x, curr_y = self._apply_adaptive_smoothing(target_x, target_y)
                    pyautogui.moveTo(curr_x, curr_y)
                    self.current_state = self.STATE_DRAG
                    feedback["state"] = self.STATE_DRAG
                    feedback["active_mode_desc"] = "Dragging... (Release pinch to drop)"
                else:
                    # During brief click window, keep cursor solidly anchored on target
                    curr_x, curr_y = self.anchor_x, self.anchor_y
                    self.current_state = "PINCHING"
                    feedback["state"] = "PINCHING"
                    feedback["active_mode_desc"] = f"Pinch held: {now - self.pinch_start_time:.2f}s"

                feedback["cursor_pos"] = (int(curr_x), int(curr_y))

            else:
                # Pinch released or not active
                if self.is_index_pinched:
                    pinch_duration = now - self.pinch_start_time
                    self.is_index_pinched = False

                    if self.is_dragging:
                        # Drop drag item
                        pyautogui.mouseUp(button='left')
                        self.is_dragging = False
                        self.current_state = self.STATE_MOVE
                        feedback["active_mode_desc"] = "Item Dropped"
                        self._play_feedback_sound(600, 30)
                    else:
                        # It was a short pinch -> Click or Double Click
                        time_since_last_click = now - self.last_click_time
                        if time_since_last_click < config.DOUBLE_CLICK_INTERVAL:
                            # Second tap within interval -> OS double click!
                            pyautogui.click(button='left')
                            self._play_feedback_sound(1600, 25)
                            self.last_click_time = 0.0
                            self.current_state = self.STATE_DOUBLE_CLICK
                            feedback["state"] = self.STATE_DOUBLE_CLICK
                            feedback["active_mode_desc"] = "Double Click Triggered!"
                            feedback["event"] = "double_click"
                            feedback["event_point"] = (landmarks[8]["x"], landmarks[8]["y"])
                        else:
                            # Single left click
                            if time_since_last_click > config.CLICK_COOLDOWN:
                                pyautogui.click(button='left')
                                self._play_feedback_sound(1200, 25)
                                self.last_click_time = now
                                self.current_state = self.STATE_LEFT_CLICK
                                feedback["state"] = self.STATE_LEFT_CLICK
                                feedback["active_mode_desc"] = "Left Click Triggered!"
                                feedback["event"] = "left_click"
                                feedback["event_point"] = (landmarks[8]["x"], landmarks[8]["y"])

                # Normal smooth cursor tracking
                curr_x, curr_y = self._apply_adaptive_smoothing(target_x, target_y)
                pyautogui.moveTo(curr_x, curr_y)
                if not feedback.get("event"):
                    self.current_state = self.STATE_MOVE
                    feedback["state"] = self.STATE_MOVE
                    feedback["active_mode_desc"] = "Aiming cursor with Index Finger"
                feedback["cursor_pos"] = (int(curr_x), int(curr_y))

        return feedback

    def cleanup(self):
        """Ensures any held mouse buttons are released upon exit."""
        if self.is_dragging:
            pyautogui.mouseUp(button='left')
            self.is_dragging = False
