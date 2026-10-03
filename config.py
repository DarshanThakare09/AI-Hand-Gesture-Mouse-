"""
AI Hand Gesture Mouse - Configuration & Settings
Customize camera resolution, gesture thresholds, active zones, and smoothing.
"""
import pyautogui

# Screen resolution (auto-detected)
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()

# Camera parameters
CAMERA_INDEX = 0
CAM_WIDTH = 640
CAM_HEIGHT = 480
TARGET_FPS = 60

# Active Interaction Frame Margin (Screen mapping zone)
# Reduced region inside camera feed mapped to the entire monitor screen.
# This prevents users from having to stretch their hand off-camera to reach screen corners.
FRAME_MARGIN_X = 110  # Horizontal margin from camera border (pixels)
FRAME_MARGIN_Y = 80   # Vertical margin from camera border (pixels)

# Cursor Stabilization & Smoothing
DEFAULT_SMOOTHING = 5.0   # Base smoothing factor (higher = smoother, lower = faster)
MIN_SMOOTHING = 1.8       # Smoothing when moving fast (low latency)
MAX_SMOOTHING = 8.0       # Smoothing when moving slowly (high precision)
DEADZONE_PIXELS = 3.5     # Ignore hand tremors smaller than this distance

# Gesture Pinch Distance Thresholds (in pixels for 640x480 frame)
CLICK_THRESHOLD = 32      # Distance between Thumb Tip and Index Tip for Left Click
RIGHT_CLICK_THRESHOLD = 34 # Distance between Thumb Tip and Middle Tip for Right Click
PINCH_RELEASE_BUFFER = 10 # Hysteresis buffer to release click cleanly

# Timing & Delays (seconds)
DRAG_HOLD_DELAY = 0.35    # Hold pinch longer than this to enter Drag & Drop mode
DOUBLE_CLICK_INTERVAL = 0.35 # Max duration between two pinches to trigger double-click
CLICK_COOLDOWN = 0.20     # Minimum time between consecutive single clicks
SCROLL_COOLDOWN = 0.04    # Interval between continuous scroll events
SCROLL_SPEED_MULTIPLIER = 1.8 # Scaling for vertical scrolling velocity

# Visual Theme (BGR Color format for OpenCV)
THEME = {
    "primary": (255, 191, 0),       # Cyber Cyan / Deep Sky
    "accent": (50, 205, 50),        # Neon Emerald Green
    "warning": (0, 140, 255),       # Vibrant Amber Orange
    "danger": (70, 70, 245),        # Neon Coral Red
    "background_dark": (20, 20, 25),# Translucent Slate Dark
    "text": (255, 255, 255),        # Pure White
    "text_muted": (180, 180, 180),  # Soft Gray
    "box_border": (255, 215, 0),    # Bright Cyan Box
    "box_fill": (255, 255, 0),      # Subtle highlight
}

# Model settings
MODEL_PATH = "hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

# Audio Feedback
ENABLE_AUDIO_FEEDBACK = False  # Toggleable with 'S' key (subtle click sound)
