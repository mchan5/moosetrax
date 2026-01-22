import cv2
import json
import os
import numpy as np

# OpenCV uses BGR format (Blue, Green, Red)
COLORS = {
    "red": (0, 0, 255),
    "green": (0, 255, 0),
    "yellow": (0, 255, 255),
    "white": (255, 255, 255),
    "black": (0, 0, 0)
}

def draw_overlay(frame, text, color_name):
    """
    Draws a semi-transparent box with centered text at the bottom of the screen.
    """
    h, w, _ = frame.shape
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.0  # Adjust based on video resolution (1.0 is good for 720p)
    thickness = 2
    margin = 10
    
    # Configure text size
    (text_w, text_h), baseline = cv2.getTextSize(text, font, scale, thickness)
    
    # Calculate Coordinates (Bottom Center)
    x = (w - text_w) // 2
    y = h - 50  # 50 pixels from bottom
    
    # 4. Draw Background Box (Black with padding)
    box_p1 = (x - margin, y + baseline + margin)
    box_p2 = (x + text_w + margin, y - text_h - margin)
    
    # Draw filled rectangle
    cv2.rectangle(frame, box_p1, box_p2, COLORS["black"], -1)
    
    # Add coloured border 
    border_color = COLORS.get(color_name, COLORS["white"])
    cv2.rectangle(frame, box_p1, box_p2, border_color, 2)

    # Draw Text
    cv2.putText(frame, text, (x, y), font, scale, COLORS["white"], thickness, cv2.LINE_AA)

def render_video(video_path, json_path, output_path):
    print(f"[VIDEO] Processing: {video_path}")
    
    # Load Data
    with open(json_path, "r") as f:
        analysis_data = json.load(f)
    
    events = analysis_data.get("timeline_events", [])
    
    # 2. Extend short events to minimum 4 seconds
    for event in events:
        duration = event["end_time"] - event["start_time"]
        if duration < 4.0:
            event["end_time"] = event["start_time"] + 4.0

    # 3. Open Video
    if not os.path.exists(video_path):
        print("[WARNING] Video file not found. Generatng a BLACK BLANK video for testing.")
        # Create a blank 5-second video @ 30fps
        cap = None
        width, height, fps = 1280, 720, 30
        total_frames = 30 * 15 # 15 seconds
    else:
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Use avc1 (H.264) codec for better browser compatibility
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_idx = 0
    print("[VIDEO] Rendering frames... (Press Ctrl+C to stop)")
    
    while True:
        # Get Frame
        if cap:
            ret, frame = cap.read()
            if not ret: break
        else:
            if frame_idx >= total_frames: break
            frame = np.zeros((height, width, 3), dtype=np.uint8) # Black frame

        # Calculate Current Time
        current_time = frame_idx / fps
        
        # Check for Events
        active_event = None
        for event in events:
            if event["start_time"] <= current_time <= event["end_time"]:
                active_event = event
                break # Only show one event at a time
        
        # Draw Overlay
        if active_event:
            draw_overlay(frame, active_event["overlay_text"], active_event["status_color"])
            
        # Write Frame
        out.write(frame)
        frame_idx += 1

        if frame_idx % 30 == 0:
            print(f" -> Processed {current_time:.1f}s / {total_frames/fps:.1f}s", end="\r")

    # Cleanup
    if cap: cap.release()
    out.release()
    print(f"\n[SUCCESS] Saved annotated video to: {output_path}")