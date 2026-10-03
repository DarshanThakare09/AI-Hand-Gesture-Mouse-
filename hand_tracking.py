"""
AI Hand Tracking Module
Built using Google MediaPipe Tasks Vision API (HandLandmarker).
Provides 21 3D hand landmarks, finger state detection, distance calculations,
and sleek visualization overlay.
"""
import os
import math
import urllib.request
import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import config

class HandTracker:
    # Standard MediaPipe 21 Landmark Connections
    CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),        # Index finger
        (5, 9), (9, 10), (10, 11), (11, 12),    # Middle finger
        (9, 13), (13, 14), (14, 15), (15, 16),  # Ring finger
        (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
        (0, 17)                                # Palm base
    ]

    # Fingertip indices
    TIP_IDS = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky

    def __init__(self, model_path=config.MODEL_PATH, num_hands=1, min_detection_confidence=0.6):
        self.model_path = model_path
        self._ensure_model_exists()
        
        # Initialize MediaPipe HandLandmarker
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_detection_confidence
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.results = None

    def _ensure_model_exists(self):
        """Auto-downloads hand_landmarker.task if not already present."""
        if not os.path.exists(self.model_path):
            print(f"[HandTracker] Downloading MediaPipe model from {config.MODEL_URL}...")
            urllib.request.urlretrieve(config.MODEL_URL, self.model_path)
            print("[HandTracker] Model downloaded successfully.")

    def find_hands(self, frame):
        """
        Processes a BGR OpenCV frame and detects hand landmarks.
        Returns:
            list_of_hands: list of landmark lists, where each landmark has (id, x, y, z) in pixel coords.
        """
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        self.results = self.detector.detect(mp_image)

        hands_landmarks = []
        if self.results.hand_landmarks:
            for hand in self.results.hand_landmarks:
                landmarks = []
                for idx, lm in enumerate(hand):
                    px, py = int(lm.x * w), int(lm.y * h)
                    landmarks.append({
                        "id": idx,
                        "x": px,
                        "y": py,
                        "norm_x": lm.x,
                        "norm_y": lm.y,
                        "norm_z": lm.z
                    })
                hands_landmarks.append(landmarks)
        return hands_landmarks

    def get_handedness(self, hand_index=0):
        """Returns 'Left' or 'Right' hand designation."""
        if self.results and self.results.handedness and len(self.results.handedness) > hand_index:
            return self.results.handedness[hand_index][0].category_name
        return "Unknown"

    def get_palm_scale(self, landmarks):
        """
        Calculates scale of the palm (wrist 0 to middle finger MCP 9).
        Used to normalize pixel distances across different distances from camera.
        """
        if not landmarks or len(landmarks) < 21:
            return 100.0
        p0 = np.array([landmarks[0]["x"], landmarks[0]["y"]])
        p9 = np.array([landmarks[9]["x"], landmarks[9]["y"]])
        dist = np.linalg.norm(p0 - p9)
        return max(35.0, float(dist))

    def get_fingers_up(self, landmarks, handedness="Right"):
        """
        Detects which fingers are extended (up = 1, down = 0).
        Orientation-invariant: combines radial wrist distance with joint hierarchy.
        Returns: [Thumb, Index, Middle, Ring, Pinky]
        """
        if not landmarks or len(landmarks) < 21:
            return [0, 0, 0, 0, 0]

        fingers = []
        wrist = np.array([landmarks[0]["x"], landmarks[0]["y"]])

        # Thumb: Distance of thumb tip (4) to pinky MCP (17) compared to IP (3) to MCP (17)
        thumb_tip = np.array([landmarks[4]["x"], landmarks[4]["y"]])
        thumb_ip = np.array([landmarks[3]["x"], landmarks[3]["y"]])
        pinky_mcp = np.array([landmarks[17]["x"], landmarks[17]["y"]])
        
        dist_tip_to_pinky = np.linalg.norm(thumb_tip - pinky_mcp)
        dist_ip_to_pinky = np.linalg.norm(thumb_ip - pinky_mcp)
        
        if dist_tip_to_pinky > dist_ip_to_pinky * 1.08:
            fingers.append(1)
        else:
            fingers.append(0)

        # 4 Fingers: Index (8), Middle (12), Ring (16), Pinky (20)
        # Robust against hand tilt: Checks radial distance from wrist plus vertical order
        for tip_id in [8, 12, 16, 20]:
            pip_id = tip_id - 2
            tip = np.array([landmarks[tip_id]["x"], landmarks[tip_id]["y"]])
            pip = np.array([landmarks[pip_id]["x"], landmarks[pip_id]["y"]])
            
            dist_wrist_tip = np.linalg.norm(wrist - tip)
            dist_wrist_pip = np.linalg.norm(wrist - pip)
            
            # Finger is extended if tip is radially extended beyond PIP joint or higher in Y
            is_extended = (dist_wrist_tip > dist_wrist_pip * 1.08) and (landmarks[tip_id]["y"] < landmarks[pip_id]["y"] + 25)
            fingers.append(1 if is_extended else 0)

        return fingers

    def get_distance(self, p1_idx, p2_idx, landmarks):
        """
        Calculates Euclidean distance and midpoint between two landmark indices.
        Returns: (distance, (mid_x, mid_y), (p1_x, p1_y), (p2_x, p2_y))
        """
        x1, y1 = landmarks[p1_idx]["x"], landmarks[p1_idx]["y"]
        x2, y2 = landmarks[p2_idx]["x"], landmarks[p2_idx]["y"]
        mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
        distance = math.hypot(x2 - x1, y2 - y1)
        return distance, (mid_x, mid_y), (x1, y1), (x2, y2)

    def draw_skeleton(self, frame, landmarks, highlight_pinch=None):
        """
        Renders a sleek futuristic cyberpunk skeletal overlay on the frame.
        """
        if not landmarks or len(landmarks) < 21:
            return

        # Draw bone connections
        for p1, p2 in self.CONNECTIONS:
            pt1 = (landmarks[p1]["x"], landmarks[p1]["y"])
            pt2 = (landmarks[p2]["x"], landmarks[p2]["y"])
            cv2.line(frame, pt1, pt2, (220, 160, 40), 2, cv2.LINE_AA)

        # Draw joints
        for lm in landmarks:
            idx = lm["id"]
            pt = (lm["x"], lm["y"])
            if idx in self.TIP_IDS:
                # Fingertips have distinctive glowing circles
                cv2.circle(frame, pt, 7, config.THEME["accent"], -1, cv2.LINE_AA)
                cv2.circle(frame, pt, 9, (255, 255, 255), 1, cv2.LINE_AA)
            else:
                # Regular joints
                cv2.circle(frame, pt, 4, config.THEME["primary"], -1, cv2.LINE_AA)

        # Index Fingertip Targeting Reticle (Landmark 8)
        index_pt = (landmarks[8]["x"], landmarks[8]["y"])
        reticle_r = 14
        cv2.circle(frame, index_pt, reticle_r, config.THEME["primary"], 1, cv2.LINE_AA)
        cv2.line(frame, (index_pt[0] - reticle_r - 4, index_pt[1]), (index_pt[0] - reticle_r + 2, index_pt[1]), config.THEME["primary"], 1, cv2.LINE_AA)
        cv2.line(frame, (index_pt[0] + reticle_r - 2, index_pt[1]), (index_pt[0] + reticle_r + 4, index_pt[1]), config.THEME["primary"], 1, cv2.LINE_AA)
        cv2.line(frame, (index_pt[0], index_pt[1] - reticle_r - 4), (index_pt[0], index_pt[1] - reticle_r + 2), config.THEME["primary"], 1, cv2.LINE_AA)
        cv2.line(frame, (index_pt[0], index_pt[1] + reticle_r - 2), (index_pt[0], index_pt[1] + reticle_r + 4), config.THEME["primary"], 1, cv2.LINE_AA)

        # Optional pinch highlight
        if highlight_pinch:
            p1, p2, is_pinched = highlight_pinch
            pt1 = (landmarks[p1]["x"], landmarks[p1]["y"])
            pt2 = (landmarks[p2]["x"], landmarks[p2]["y"])
            color = config.THEME["accent"] if is_pinched else config.THEME["warning"]
            cv2.line(frame, pt1, pt2, color, 3, cv2.LINE_AA)
            mid = ((pt1[0] + pt2[0]) // 2, (pt1[1] + pt2[1]) // 2)
            cv2.circle(frame, mid, 6, color, -1, cv2.LINE_AA)
