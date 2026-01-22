# --- Imports and Config ---
import cv2
import mediapipe as mp
import numpy as np
import os
import csv
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MIN_CONFIDENCE = 0.4
LANDMARK_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner", 
    "right_eye", "right_eye_outer", "left_ear", "right_ear", "mouth_left", 
    "mouth_right", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow", 
    "left_wrist", "right_wrist", "left_pinky", "right_pinky", "left_index", 
    "right_index", "left_thumb", "right_thumb", "left_hip", "right_hip", 
    "left_knee", "right_knee", "left_ankle", "right_ankle", "left_heel", 
    "right_heel", "left_foot_index", "right_foot_index"
]
SMOOTHING_WINDOW_SIZE = 25
MODEL_PATH = os.path.join(os.path.dirname(__file__), "mediapipe", "pose_landmarker_lite.task")

def smooth_landmarks(landmarks_history):
    smoothed_landmarks = []
    for i in range(len(landmarks_history[0])):
        x_vals = [landmarks_history[j][i][0] for j in range(len(landmarks_history))]
        y_vals = [landmarks_history[j][i][1] for j in range(len(landmarks_history))]
        z_vals = [landmarks_history[j][i][2] for j in range(len(landmarks_history))]
        vis_vals = [landmarks_history[j][i][3] for j in range(len(landmarks_history))]
        smoothed_x = np.mean(x_vals)
        smoothed_y = np.mean(y_vals)
        smoothed_z = np.mean(z_vals)
        smoothed_vis = np.mean(vis_vals)
        smoothed_landmarks.append((smoothed_x, smoothed_y, smoothed_z, smoothed_vis))
    return smoothed_landmarks

def get_confidence_color(confidence):
    green = int(255 * confidence)
    red = int(255 * (1 - confidence))
    return (0, green, red)

def compute_body_metrics(landmarks):
    # Returns (height, shoulder_width) in normalized units (not cm)
    # height: mean of left_shoulder-to-left_ankle and right_shoulder-to-right_ankle
    def dist(a, b):
        return np.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)
    try:
        l_shoulder = landmarks[LANDMARK_NAMES.index('left_shoulder')][:3]
        r_shoulder = landmarks[LANDMARK_NAMES.index('right_shoulder')][:3]
        l_ankle = landmarks[LANDMARK_NAMES.index('left_ankle')][:3]
        r_ankle = landmarks[LANDMARK_NAMES.index('right_ankle')][:3]
        height = (dist(l_shoulder, l_ankle) + dist(r_shoulder, r_ankle)) / 2
        shoulder_width = dist(l_shoulder, r_shoulder)
        return height, shoulder_width
    except Exception:
        return np.nan, np.nan

def process_video(video_path, output_csv_path):
    """
    Extracts pose landmarks from video, smooths, and writes to CSV with body metrics in header.
    """
    if not os.path.exists(os.path.dirname(output_csv_path)):
        os.makedirs(os.path.dirname(output_csv_path))

    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=MIN_CONFIDENCE,
        min_pose_presence_confidence=MIN_CONFIDENCE,
        min_tracking_confidence=MIN_CONFIDENCE
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    print(f"[DEBUG] Opening video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Failed to open video: {video_path}")
        return
    fps = cap.get(cv2.CAP_PROP_FPS)
    width, height_px = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[DEBUG] FPS: {fps}, Width: {width}, Height: {height_px}")

    landmark_history = []
    first_valid_landmarks = None
    with open(output_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        header = ['frame', 'timestamp_ms']
        for name in LANDMARK_NAMES:
            header.extend([f'{name}_x', f'{name}_y', f'{name}_z', f'{name}_vis'])
        frame_idx = 0
        last_timestamp_ms = -1
        wrote_metrics = False
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print(f"[DEBUG] No more frames to read at frame {frame_idx}.")
                break
            timestamp_ms = int(1000 * frame_idx / fps)
            if timestamp_ms <= last_timestamp_ms:
                timestamp_ms = last_timestamp_ms + 1  # Force monotonic increase
            last_timestamp_ms = timestamp_ms
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            result = detector.detect_for_video(mp_image, timestamp_ms)
            row = [frame_idx, timestamp_ms]
            if result.pose_landmarks:
                print(f"[DEBUG] Landmarks detected at frame {frame_idx}.")
                landmarks = result.pose_landmarks[0]
                landmarks_data = [(lm.x, lm.y, lm.z, lm.visibility) for lm in landmarks]
                landmark_history.append(landmarks_data)
                if not wrote_metrics:
                    height_val, shoulder_width_val = compute_body_metrics(landmarks_data)
                    f.write(f"# height={height_val}\n")
                    f.write(f"# shoulder_width={shoulder_width_val}\n")
                    writer.writerow(header)
                    wrote_metrics = True
                if len(landmark_history) > SMOOTHING_WINDOW_SIZE:
                    landmark_history.pop(0)
                smoothed_landmarks = smooth_landmarks(landmark_history)
                for smoothed_lm in smoothed_landmarks:
                    row.extend(smoothed_lm)
                # Visualization (optional):
                for lm in smoothed_landmarks:
                    cx, cy = int(lm[0] * width), int(lm[1] * height_px)
                    color = get_confidence_color(lm[3])
                    cv2.circle(frame, (cx, cy), 5, color, -1)
                    cv2.circle(frame, (cx, cy), 6, (255, 255, 255), 1)
            else:
                print(f"[DEBUG] No landmarks detected at frame {frame_idx}.")
                row.extend([np.nan] * (len(LANDMARK_NAMES) * 4))
                if not wrote_metrics:
                    f.write(f"# height=nan\n# shoulder_width=nan\n")
                    writer.writerow(header)
                    wrote_metrics = True
            cv2.putText(frame, f"MODE: TASKS_V1 (Video)", (20, 40), 1, 1.5, (0, 255, 0), 2)
            writer.writerow(row)
            # cv2.imshow("Multi-Sport Analysis", frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'): break
            frame_idx += 1
    detector.close()
    cap.release()
    cv2.destroyAllWindows()

# CLI entry point for testing
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract pose landmarks and body metrics from video.")
    parser.add_argument('--video', type=str, required=True, help='Path to input video file')
    parser.add_argument('--output', type=str, required=True, help='Path to output CSV file')
    args = parser.parse_args()
    process_video(args.video, args.output)
