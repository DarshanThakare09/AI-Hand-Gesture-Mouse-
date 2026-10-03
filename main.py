"""
AI Hand Gesture Mouse - Main Application
Real-time vision pipeline orchestrating webcam feed, hand landmark detection,
gesture recognition, adaptive cursor smoothing, and cyber HUD display.
"""
import time
import sys
import cv2
import config
from hand_tracking import HandTracker
from gesture_controller import GestureController
from ui_hud import UIHud

def print_banner():
    banner = r"""
  =======================================================
     ____  _   _    __  __                          
    / __ \(_) (_)  |  \/  |                         
   / / _` | |  _   | \  / | ___  _   _ ___  ___     
  | | (_| | | | |  | |\/| |/ _ \| | | / __|/ _ \    
   \ \__,_|_|_| |_ |_|  |_|\___/ \__,_\___/\___|    
    \____/   \___/                                  
    AI Hand Gesture Virtual Mouse Controller
    B-Tech Artificial Intelligence Project
  =======================================================
    Keyboard Shortcuts:
      [M] or [P] : Pause / Resume Mouse Control
      [H]        : Toggle Gesture Manual on/off
      [S]        : Toggle Audio Feedback Beep
      [C]        : Re-center Mouse to Screen Center
      [Q] / ESC  : Quit Application
  =======================================================
    """
    print(banner)

def main():
    print_banner()

    print("[Main] Initializing Webcam (Index: {})...".format(config.CAMERA_INDEX))
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)

    if not cap.isOpened():
        print("[Error] Could not open webcam. Please verify camera connection and permissions.")
        sys.exit(1)

    print("[Main] Initializing MediaPipe Hand Tracking Engine...")
    tracker = HandTracker(model_path=config.MODEL_PATH, num_hands=1)
    
    print("[Main] Initializing Gesture Controller...")
    controller = GestureController()
    
    print("[Main] Initializing Futuristic HUD...")
    hud = UIHud()

    window_name = "AI Hand Gesture Virtual Mouse"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    prev_time = time.time()
    fps = 0.0

    print("[Main] System Online! Position your hand in the camera view to control your PC.")

    try:
        while True:
            success, frame = cap.read()
            if not success or frame is None:
                print("[Warning] Empty frame received from webcam. Retrying...")
                time.sleep(0.01)
                continue

            # Mirror frame horizontally for natural intuitive navigation
            frame = cv2.flip(frame, 1)

            # Calculate FPS
            curr_time = time.time()
            dt = curr_time - prev_time
            prev_time = curr_time
            if dt > 0:
                current_fps = 1.0 / dt
                # Smooth FPS readout
                fps = 0.9 * fps + 0.1 * current_fps if fps > 0 else current_fps

            # Detect hand landmarks
            hands = tracker.find_hands(frame)
            handedness = "Right"

            if hands:
                primary_hand = hands[0]
                handedness = tracker.get_handedness(0)
                
                # Execute gesture interpretation & cursor mapping
                feedback = controller.process(tracker, primary_hand)
                
                # Draw cyberpunk skeleton
                is_pinched = feedback.get("is_pinched", False)
                tracker.draw_skeleton(frame, primary_hand, highlight_pinch=(4, 8, is_pinched))
            else:
                # No hand in frame
                controller.scroll_ref_y = None
                feedback = {
                    "state": "NO HAND DETECTED",
                    "cursor_pos": (int(controller.prev_x), int(controller.prev_y)),
                    "index_pinch_dist": 100.0,
                    "middle_pinch_dist": 100.0,
                    "is_pinched": False,
                    "is_dragging": False,
                    "active_mode_desc": "Wave your hand inside the active box"
                }

            # Render futuristic Cyber HUD
            hud.render(frame, feedback, fps, handedness)

            # Display composite visual output
            cv2.imshow(window_name, frame)

            # Keyboard controls
            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), ord('Q'), 27]: # 'q' or ESC
                print("[Main] Exit requested by user.")
                break
            elif key in [ord('m'), ord('M'), ord('p'), ord('P')]:
                is_paused = controller.toggle_pause()
                status = "PAUSED" if is_paused else "RESUMED"
                print(f"[Main] Mouse Control {status}")
            elif key in [ord('h'), ord('H')]:
                hud.toggle_guide()
            elif key in [ord('s'), ord('S')]:
                audio_status = controller.toggle_audio()
                status = "ENABLED" if audio_status else "DISABLED"
                print(f"[Main] Click Audio Feedback {status}")
            elif key in [ord('c'), ord('C')]:
                # Center cursor
                controller.prev_x = config.SCREEN_WIDTH // 2
                controller.prev_y = config.SCREEN_HEIGHT // 2
                print("[Main] Cursor re-centered to screen midpoint.")

    except KeyboardInterrupt:
        print("\n[Main] Application interrupted by user.")
    finally:
        print("[Main] Cleaning up resources...")
        controller.cleanup()
        cap.release()
        cv2.destroyAllWindows()
        print("[Main] Shutdown complete.")

if __name__ == "__main__":
    main()
