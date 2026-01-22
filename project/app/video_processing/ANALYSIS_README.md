"""
Multi-Rep Exercise Analysis & Comparison System
===============================================

This module provides comprehensive analysis and comparison of exercise videos with:
- Multi-rep detection and tracking
- Time-warped ground-truth comparison
- Tolerance-based deviation detection
- LLM-ready annotation generation

KEY FUNCTIONS:
==============

1. analyze(data) -> (angles, speeds, accelerations, symmetry_scores, angular_speeds, signed_speeds_y, reps, data)
   - Extracts all features from raw pose data
   - Detects all reps (multiple reps supported)
   - Calculates per-rep metrics (duration, max_depth, rest periods)
   - Output: rep_advanced_metrics.csv (frame-by-frame + rep summaries)

2. compare_exercises(gt_csv_path, comparison_csv_path, output_path, summary_path, is_ground_truth_first)
   - Treats first CSV as ground truth reference
   - Calculates averaged GT metrics across all reps
   - Time-warps GT signals to match each comparison rep's duration
   - Flags frames where signals exceed tolerance thresholds
   - Output: 
     - comparison_results.csv (frame-by-frame with annotations)
     - comparison_summary.csv (per-rep summary with scores)
     - comparison_visualization.png (signal overlays)

3. warp_signals_to_duration(signals_dict, original_frames, target_frames)
   - Interpolates signal arrays to match target rep duration
   - Used for dynamic time-warping during comparison

CONFIGURATION (editable):
=========================

SIGNAL_TOLERANCES:
- 'angle': 5.0 degrees (joint angles)
- 'speed': 0.10 (10% of signal value)
- 'acceleration': 0.10 (10% of signal value)
- 'symmetry': 2.0 degrees
- 'angular_speed': 5.0 degrees/second

JOINT_WEIGHT: 0.70 (70% weight on joint metrics for form quality)
SYMMETRY_WEIGHT: 0.30 (30% weight on symmetry metrics)

OUTPUT CSV STRUCTURES:
=====================

rep_advanced_metrics.csv:
- Columns: frame, timestamp_ms, rep_id, [all signals], rep_start_frame, rep_end_frame, max_depth_frame, 
  max_depth_value, avg_speed_left_elbow, avg_speed_right_elbow, rep_duration_ms, rest_duration_before_ms
- rep_id: 0, 1, 2... for frames in reps; NaN for rest periods
- Rep summary values populated for all frames in that rep (for easy filtering/grouping)

comparison_results.csv (detailed frame-by-frame comparison):
- Columns: [all frame columns from comparison rep] + annotation columns
- Annotation columns present only for frames exceeding tolerance:
  {signal_name}_annotation: "joint_name|gt_value|actual_value|difference"

comparison_summary.csv (per-rep summary):
- rep_id: Rep ID in comparison video
- rep_frames: Number of frames in this rep
- flagged_frames: Number of frames where signals exceeded tolerance
- flagged_ratio: Fraction of rep frames flagged
- primary_joint_deviations: Top 3 deviating joints with magnitudes
- form_quality_score: 0-100% (70% weighted on joint metrics)
- symmetry_quality_score: 0-100% (based on symmetry deviations)
- overall_score: Weighted combination (70% form + 30% symmetry)

SIGNAL TYPES & COLUMN NAMING:
=============================

Angles (8 total):
- left_elbow, right_elbow, left_knee, right_knee, left_hip, right_hip, left_ankle, right_ankle

Speeds (per keypoint, 33 total):
- {keypoint}_speed (3D Euclidean velocity, m/s or normalized units)

Accelerations (per keypoint, 33 total):
- {keypoint}_acceleration (change in speed, units/s²)

Angular Speeds (per angle, 8 total):
- {angle_name}_angular_speed (degrees/second)

Signed Y-Velocities (per keypoint, 33 total):
- {keypoint}_signed_speed_y (vertical component, + for up, - for down)

Symmetry Scores (5 total):
- shoulder_position_symmetry: L-R shoulder distance
- elbow_angle_symmetry: |left_elbow_angle - right_elbow_angle|
- knee_angle_symmetry: |left_knee_angle - right_knee_angle|
- hip_angle_symmetry: |left_hip_angle - right_hip_angle|
- ankle_angle_symmetry: |left_ankle_angle - right_ankle_angle|

WORKFLOW EXAMPLE:
================

# Stage 1: Analyze raw video
from analysis import analyze
import pandas as pd

data = pd.read_csv('pose_outputs/biomechanical_data.csv')
analyze(data)  # Generates rep_advanced_metrics.csv

# Stage 2: Compare two videos
from analysis import compare_exercises

detailed, summary = compare_exercises(
    'pose_outputs/ground_truth_metrics.csv',  # Reference video
    'pose_outputs/user_video_metrics.csv',    # User's attempt
    'pose_outputs/comparison_results.csv',
    'pose_outputs/comparison_summary.csv'
)

# Stage 3: Send to LLM
# Read comparison_results.csv and comparison_summary.csv
# Extract flagged frames and annotations
# Send to LLM with instruction to generate natural language feedback

NOTES:
======

- Rest periods are identified by missing rep_id values (NaN)
- Each frame in a rep contains rep summary metrics (start_frame, end_frame, etc.) for easy grouping
- Time-warping allows fair comparison of reps with different durations
- Tolerances are configurable and signal-specific
- Form quality score weights joints (70%) higher than symmetry (30%)
- Annotations contain only metric values (no prose) for cleaner LLM processing
"""

if __name__ == '__main__':
    print(__doc__)
