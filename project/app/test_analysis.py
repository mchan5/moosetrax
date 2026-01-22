#!/usr/bin/env python3
import sys, os
from pathlib import Path
import pandas as pd, numpy as np
import warnings
warnings.filterwarnings('ignore')

# Ensure script runs from correct directory
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
os.chdir(backend_dir)

# Set up paths
from video_processing.analysis import process_signals, warp_signals_to_duration, SIGNAL_TOLERANCES, JOINT_WEIGHT, SYMMETRY_WEIGHT, JOINT_SIGNALS, SYMMETRY_SIGNALS, read_body_metrics_from_csv, normalize_signals
from video_processing.video_handler import process_video
from full_pipeline import run_pipeline as run_full_pipeline

def get_signal_type(signal_name):
    if 'symmetry' in signal_name: return 'symmetry'
    elif 'angular_speed' in signal_name: return 'angular_speed'
    elif 'speed' in signal_name: return 'speed'
    elif 'acceleration' in signal_name: return 'acceleration'
    else: return 'angle'

def get_tolerance(signal_type, gt_value):
    if signal_type == 'symmetry': return SIGNAL_TOLERANCES['symmetry']
    elif signal_type == 'angular_speed': return SIGNAL_TOLERANCES['angular_speed']
    elif signal_type == 'speed': return abs(gt_value * SIGNAL_TOLERANCES['speed']) if gt_value != 0 else 0.05
    elif signal_type == 'acceleration': return abs(gt_value * SIGNAL_TOLERANCES['acceleration']) if gt_value != 0 else 0.05
    else: return SIGNAL_TOLERANCES['angle']

def extract_joint(signal_name):
    parts = signal_name.split('_')
    if len(parts) >= 2 and parts[0] in ['left', 'right']:
        return f"{parts[0]}_{parts[1]}"
    return signal_name

def annotation_text(signal, user_val, gt_val, tol, diff):
    pct = 100 * abs(diff) / tol if tol else 0
    if abs(diff) > tol:
        if diff > 0:
            return f"{signal}: {user_val:.2f} > GT {gt_val:.2f} (tol {tol:.2f}) by {diff:.2f} [{pct:.1f}% over]"
        else:
            return f"{signal}: {user_val:.2f} < GT {gt_val:.2f} (tol {tol:.2f}) by {abs(diff):.2f} [{pct:.1f}% over]"
    return ""

def analyze(USER_VIDEO):
    # Accept video paths as args or use defaults
    backend_dir = os.getcwd()
    GT_VIDEO = os.environ.get('GT_VIDEO', os.path.join(backend_dir, 'app/video_processing/data_temp/IMG_2221.MOV'))
    if USER_VIDEO.startswith('./'):
        USER_VIDEO = os.path.join(backend_dir, 'app', USER_VIDEO[2:])
    GT_CSV = os.path.join(backend_dir, 'app/pose_outputs/gt_raw.csv')
    USER_CSV = os.path.join(backend_dir, 'app/pose_outputs/user_raw.csv')

    print(f"Processing GT video: {GT_VIDEO}")
    process_video(GT_VIDEO, GT_CSV)
    print(f"Processing USER video: {USER_VIDEO}")
    process_video(USER_VIDEO, USER_CSV)

    # Read body metrics
    gt_height, gt_shoulder = read_body_metrics_from_csv(GT_CSV)
    user_height, user_shoulder = read_body_metrics_from_csv(USER_CSV)

    # Analyze GT (expect 1 rep)
    gt_df = pd.read_csv(GT_CSV, comment='#')
    gt_results = process_signals(gt_df, expected_reps=1)
    gt_reps = gt_results['reps']
    if len(gt_reps) != 1:
        raise RuntimeError(f"GT video must have exactly 1 rep, found {len(gt_reps)}")
    # Only keep joint angles and their angular speeds/accelerations
    joint_names = ['left_elbow', 'right_elbow', 'left_knee', 'right_knee', 'left_hip', 'right_hip', 'left_ankle', 'right_ankle']
    gt_signals = {k: v for k, v in gt_results['angles'].items() if k in joint_names}
    for k, v in gt_results['angular_speeds'].items():
        if k in joint_names:
            gt_signals[f'{k}_angular_speed'] = v
    for k, v in gt_results['accelerations'].items():
        if k in joint_names:
            gt_signals[f'{k}_acceleration'] = v
    gt_signals = normalize_signals(gt_signals, gt_height)
    gt_profile = {k: np.nanmean([x for x in v if not np.isnan(x)]) for k, v in gt_signals.items()}
    signal_cols = list(gt_signals.keys())

    # Analyze USER (expect 3 reps)
    user_df = pd.read_csv(USER_CSV, comment='#')
    user_results = process_signals(user_df, expected_reps=1)
    user_reps = user_results['reps']
    if len(user_reps) != 1:
        raise RuntimeError(f"User video must have exactly 1 rep, found {len(user_reps)}")
    user_signals = {k: v for k, v in user_results['angles'].items() if k in joint_names}
    for k, v in user_results['angular_speeds'].items():
        if k in joint_names:
            user_signals[f'{k}_angular_speed'] = v
    for k, v in user_results['accelerations'].items():
        if k in joint_names:
            user_signals[f'{k}_acceleration'] = v
    user_signals = normalize_signals(user_signals, user_height)
    # --- Generate summary doc ---
    summary_lines = []
    # Rep length and rest time
    gt_rep = gt_reps[0]
    user_rep = user_reps[0]
    gt_length = gt_rep['end_frame'] - gt_rep['start_frame'] + 1
    user_length = user_rep['end_frame'] - user_rep['start_frame'] + 1
    # Calculate rest time as time between frame 0 and start frame (in frames and ms)
    gt_rest_frames = gt_rep['start_frame']
    user_rest_frames = user_rep['start_frame']
    # If you have fps, you can convert to ms; otherwise, just show frames
    summary_lines.append(f"GT rep length: {gt_length} frames, rest before: {gt_rest_frames} frames")
    summary_lines.append(f"User rep length: {user_length} frames, rest before: {user_rest_frames} frames")

    # Issues: compare joint angles and speeds
    for signal in signal_cols:
        gt_val = np.nanmean([x for x in gt_signals[signal][gt_rep['start_frame']:gt_rep['end_frame']+1] if not np.isnan(x)])
        user_val = np.nanmean([x for x in user_signals[signal][user_rep['start_frame']:user_rep['end_frame']+1] if not np.isnan(x)])
        diff = user_val - gt_val
        tol = get_tolerance(get_signal_type(signal), gt_val)
        if abs(diff) > tol:
            summary_lines.append(f"{signal}: User {user_val:.2f} vs GT {gt_val:.2f} (diff {diff:.2f}, tol {tol:.2f}) [ISSUE]")
        else:
            summary_lines.append(f"{signal}: User {user_val:.2f} vs GT {gt_val:.2f} (diff {diff:.2f}, tol {tol:.2f}) [OK]")

    # Timestamps for start/end/max depth
    summary_lines.append(f"GT rep: start {gt_rep['start_frame']}, end {gt_rep['end_frame']}, max depth {gt_rep['max_depth_frame']}")
    summary_lines.append(f"User rep: start {user_rep['start_frame']}, end {user_rep['end_frame']}, max depth {user_rep['max_depth_frame']}")

    # Write summary to file
    backend_dir = os.getcwd()
    summary_path = os.path.join(backend_dir, 'app/pose_outputs/final_summary.txt')
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, 'w') as f:
        f.write('\n'.join(summary_lines))
    print("✓ final_summary.txt generated")
    user_signals = {k: v for k, v in user_results['angles'].items() if k in joint_names}
    for k, v in user_results['angular_speeds'].items():
        if k in joint_names:
            user_signals[f'{k}_angular_speed'] = v
    for k, v in user_results['accelerations'].items():
        if k in joint_names:
            user_signals[f'{k}_acceleration'] = v
    user_signals = normalize_signals(user_signals, user_height)
    import matplotlib.pyplot as plt
    # # --- GT Visualization ---
    # plt.figure(figsize=(16, 8))
    # for signal in signal_cols:
    #     plt.plot(gt_df['frame'], gt_signals[signal], label=signal)
    # for rep in gt_reps:
    #     plt.axvspan(rep['start_frame'], rep['end_frame'], color='green', alpha=0.1)
    #     plt.axvline(rep['max_depth_frame'], color='red', linestyle=':', alpha=0.7)
    #     plt.text(rep['max_depth_frame'], plt.ylim()[1]*0.95, f"max {rep['max_depth_frame']}", color='red', fontsize=8, ha='center')
    # plt.title('GT: All Joint Angles, Speeds, Accelerations')
    # plt.xlabel('Frame')
    # plt.ylabel('Value')
    # plt.legend()
    # plt.tight_layout()
    # plt.show()

    # # --- USER Visualization ---
    # plt.figure(figsize=(16, 8))
    # for signal in signal_cols:
    #     plt.plot(user_df['frame'], user_signals[signal], label=signal)
    # for rep in user_reps:
    #     plt.axvspan(rep['start_frame'], rep['end_frame'], color='blue', alpha=0.1)
    #     plt.axvline(rep['max_depth_frame'], color='red', linestyle=':', alpha=0.7)
    #     plt.text(rep['max_depth_frame'], plt.ylim()[1]*0.95, f"max {rep['max_depth_frame']}", color='red', fontsize=8, ha='center')
    # plt.title('USER: All Joint Angles, Speeds, Accelerations')
    # plt.xlabel('Frame')
    # plt.ylabel('Value')
    # plt.legend()
    # plt.tight_layout()
    # plt.show()

    # Build comparison CSV
    comparison_rows = []
    prev_end = None
    for user_rep in user_reps:
        rep_id = user_rep['rep_id']
        rep_start = user_rep['start_frame']
        rep_end = user_rep['end_frame']
        rep_size = rep_end - rep_start + 1
        rest_ms_before = user_rep.get('rest_duration_before_ms', 0)
        # Extract this rep's signals
        rep_signals = {sig: user_signals[sig][rep_start:rep_end+1] for sig in signal_cols}
        # Warp GT profile to match this rep's duration
        gt_warped = warp_signals_to_duration(gt_profile, len(gt_df), rep_size)
        for local_frame in range(rep_size):
            row = {
                'rep_id': rep_id,
                'frame_in_rep': local_frame,
                'frame_absolute': rep_start + local_frame,
                'rest_ms_before': rest_ms_before if local_frame == 0 else 0
            }
            for signal in signal_cols:
                actual = rep_signals[signal][local_frame]
                gt_val = gt_warped.get(signal, [np.nan])[local_frame]
                diff = actual - gt_val if not (np.isnan(actual) or np.isnan(gt_val)) else np.nan
                sig_type = get_signal_type(signal)
                tol = get_tolerance(sig_type, gt_val)
                row[f'{signal}_user'] = actual
                row[f'{signal}_gt'] = gt_val
                row[f'{signal}_diff'] = diff
                row[f'{signal}_flagged'] = int(abs(diff) > tol) if not np.isnan(diff) and not np.isnan(tol) else 0
                row[f'{signal}_annotation'] = annotation_text(signal, actual, gt_val, tol, diff) if abs(diff) > tol and not np.isnan(diff) else ''
            comparison_rows.append(row)
    comparison_df = pd.DataFrame(comparison_rows)
    backend_dir = os.getcwd()
    comparison_path = os.path.join(backend_dir, 'app/pose_outputs/user_comparison.csv')
    os.makedirs(os.path.dirname(comparison_path), exist_ok=True)
    comparison_df.to_csv(comparison_path, index=False)
    print(f"✓ user_comparison.csv ({len(comparison_df)} rows)")

    if not run_full_pipeline(USER_VIDEO): 
        return False 
    return True 

if __name__ == "__main__":
    analyze('./video_processing/data_temp/2222_clip.mp4')
