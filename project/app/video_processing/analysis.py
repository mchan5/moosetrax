def calculate_symmetry(data, angles):
    """
    Calculate symmetry metrics for key joints and positions.
    Args:
        data: DataFrame with normalized pose coordinates
        angles: Dict of joint angles (from extract_joint_angles)
    Returns:
        Dict of symmetry scores per frame (e.g., left/right angle diffs, position symmetry)
    """
    symmetry = {
        'shoulder_position_symmetry': [],
        'elbow_angle_symmetry': [],
        'knee_angle_symmetry': [],
        'hip_angle_symmetry': [],
        'ankle_angle_symmetry': []
    }
    n_frames = len(data)
    for i in range(n_frames):
        # Position symmetry: x-coord difference between left/right shoulders
        try:
            l_shoulder_x = float(data.loc[i, 'left_shoulder_x'])
            r_shoulder_x = float(data.loc[i, 'right_shoulder_x'])
            symmetry['shoulder_position_symmetry'].append(abs(l_shoulder_x + r_shoulder_x))
        except Exception:
            symmetry['shoulder_position_symmetry'].append(np.nan)
        # Angle symmetry: difference between left/right joint angles
        for joint, key in [
            ('elbow', 'elbow_angle_symmetry'),
            ('knee', 'knee_angle_symmetry'),
            ('hip', 'hip_angle_symmetry'),
            ('ankle', 'ankle_angle_symmetry')
        ]:
            l_name = f'left_{joint}'
            r_name = f'right_{joint}'
            try:
                l_angle = float(angles[l_name][i])
                r_angle = float(angles[r_name][i])
                symmetry[key].append(abs(l_angle - r_angle))
            except Exception:
                symmetry[key].append(np.nan)
    return symmetry
import pandas as pd
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from scipy.interpolate import interp1d

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

CONFIDENCE_THRESHOLD = 0.7  # Adjust as needed

# ======================= CONFIGURABLE TOLERANCES =======================
SIGNAL_TOLERANCES = {
    'angle': 15.0,  # degrees
    'speed': 0.20,  # 10% of signal range
    'acceleration': 0.10,  # 10% of signal range
    'symmetry': 2.0,  # degrees
    'angular_speed': 5.0  # degrees/second
}

# Joint weighting for form quality score
JOINT_WEIGHT = 0.70  # 70% for joint metrics
SYMMETRY_WEIGHT = 0.30  # 30% for symmetry metrics

# Keypoints for weighting
JOINT_SIGNALS = {
    'left_elbow', 'right_elbow', 'left_knee', 'right_knee',
    'left_hip', 'right_hip', 'left_ankle', 'right_ankle'
}

SYMMETRY_SIGNALS = {
    'shoulder_position_symmetry', 'elbow_angle_symmetry', 'knee_angle_symmetry',
    'hip_angle_symmetry', 'ankle_angle_symmetry'
}

# ======================= SIGNAL WARPING =======================
def warp_signals_to_duration(signals_dict, original_frames, target_frames):
    """
    Time-warp signal arrays from original frame count to target frame count using interpolation.
    
    Args:
        signals_dict: Dictionary of signal_name -> array
        original_frames: Original number of frames
        target_frames: Target number of frames (for comparison rep)
    
    Returns:
        Dictionary of warped signal_name -> warped_array
    """
    if original_frames == target_frames:
        return {k: np.array(v) for k, v in signals_dict.items()}
    
    warped = {}
    original_indices = np.linspace(0, original_frames - 1, original_frames)
    target_indices = np.linspace(0, original_frames - 1, target_frames)
    
    for signal_name, signal_array in signals_dict.items():
        signal_array = np.array(signal_array)
        # Handle NaN values by interpolating only valid points
        valid_mask = ~np.isnan(signal_array)
        if np.any(valid_mask):
            valid_indices = original_indices[valid_mask]
            valid_values = signal_array[valid_mask]
            if len(valid_indices) > 1:
                f = interp1d(valid_indices, valid_values, kind='linear', fill_value='extrapolate')
                warped[signal_name] = f(target_indices)
            else:
                warped[signal_name] = np.full(target_frames, valid_values[0])
        else:
            warped[signal_name] = np.full(target_frames, np.nan)
    
    return warped

# Define smoothing function to apply to x, y, z coordinates
def smooth_data(data, sigma=2):
    return gaussian_filter1d(data, sigma=sigma, axis=0)

# Normalize function: using distance between shoulders and feet to estimate height
def estimate_height(data):
    # Use mean positions for height estimation
    left_shoulder = np.array([data['left_shoulder_x'].mean(), data['left_shoulder_y'].mean(), data['left_shoulder_z'].mean()])
    right_shoulder = np.array([data['right_shoulder_x'].mean(), data['right_shoulder_y'].mean(), data['right_shoulder_z'].mean()])
    left_foot = np.array([data['left_foot_index_x'].mean(), data['left_foot_index_y'].mean(), data['left_foot_index_z'].mean()])
    right_foot = np.array([data['right_foot_index_x'].mean(), data['right_foot_index_y'].mean(), data['right_foot_index_z'].mean()])

    # Distance between shoulders and feet to estimate height
    shoulder_to_foot = np.linalg.norm(left_shoulder - left_foot) + np.linalg.norm(right_shoulder - right_foot)
    height = shoulder_to_foot / 2  # Rough average height estimate
    return height

# Normalize coordinates based on estimated height
def normalize_coordinates(data, height):
    for column in data.columns:
        if 'x' in column or 'y' in column or 'z' in column:
            data[column] = data[column] / height
    return data

# Calculate angle between three points
def calculate_angle(p1, p2, p3):
    v1 = p1 - p2
    v2 = p3 - p2
    cosine_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

# Extract joint angles: Example for elbow (shoulder, elbow, wrist)
def extract_joint_angles(data):
    angles = {
        'left_elbow': [],
        'right_elbow': [],
        'left_knee': [],
        'right_knee': [],
        'left_hip': [],
        'right_hip': [],
        'left_ankle': [],
        'right_ankle': []
    }
    
    # Loop over each frame in the dataset
    for i in range(len(data)):
        # Check confidence for keypoints and set to NaN if below threshold
        def get_point(keypoint):
            # Try _conf first (confidence), then _vis (visibility) for MediaPipe format
            conf_col = f'{keypoint}_conf' if f'{keypoint}_conf' in data.columns else f'{keypoint}_vis'
            conf = data.loc[i, conf_col] if conf_col in data.columns else 1.0
            if conf < CONFIDENCE_THRESHOLD:
                return np.array([np.nan, np.nan, np.nan])
            return np.array([data.loc[i, f'{keypoint}_x'], data.loc[i, f'{keypoint}_y'], data.loc[i, f'{keypoint}_z']])
        
        # Elbow angles
        left_shoulder = get_point('left_shoulder')
        left_elbow = get_point('left_elbow')
        left_wrist = get_point('left_wrist')
        angles['left_elbow'].append(calculate_angle(left_shoulder, left_elbow, left_wrist) if not np.isnan(left_elbow).any() else np.nan)
        
        right_shoulder = get_point('right_shoulder')
        right_elbow = get_point('right_elbow')
        right_wrist = get_point('right_wrist')
        angles['right_elbow'].append(calculate_angle(right_shoulder, right_elbow, right_wrist) if not np.isnan(right_elbow).any() else np.nan)
        
        # Knee angles
        left_hip = get_point('left_hip')
        left_knee = get_point('left_knee')
        left_ankle = get_point('left_ankle')
        angles['left_knee'].append(calculate_angle(left_hip, left_knee, left_ankle) if not np.isnan(left_knee).any() else np.nan)
        
        right_hip = get_point('right_hip')
        right_knee = get_point('right_knee')
        right_ankle = get_point('right_ankle')
        angles['right_knee'].append(calculate_angle(right_hip, right_knee, right_ankle) if not np.isnan(right_knee).any() else np.nan)
        
        # Hip angles (angle at hip: shoulder, hip, knee)
        angles['left_hip'].append(calculate_angle(left_shoulder, left_hip, left_knee) if not np.isnan(left_hip).any() else np.nan)
        angles['right_hip'].append(calculate_angle(right_shoulder, right_hip, right_knee) if not np.isnan(right_hip).any() else np.nan)
        
        # Ankle angles (angle at ankle: knee, ankle, foot_index)
        left_foot = get_point('left_foot_index')
        angles['left_ankle'].append(calculate_angle(left_knee, left_ankle, left_foot) if not np.isnan(left_ankle).any() else np.nan)
        
        right_foot = get_point('right_foot_index')
        angles['right_ankle'].append(calculate_angle(right_knee, right_ankle, right_foot) if not np.isnan(right_ankle).any() else np.nan)

    return angles

# Calculate speed and acceleration of keypoints as 3D Euclidean distance
def calculate_speed(data):
    speeds = {}
    accelerations = {}
    signed_speeds_y = {}  # Signed y-velocity
    for column in data.columns:
        if '_x' in column:  # Only process x columns to avoid duplicates
            keypoint = column.replace('_x', '')  # Extract keypoint name
            
            if keypoint not in speeds:
                speeds[keypoint] = []
                accelerations[keypoint] = []
                signed_speeds_y[keypoint] = []
            
            # Get x, y, z for current and next frame, check confidence
            for i in range(len(data) - 1):
                conf_col = f'{keypoint}_conf' if f'{keypoint}_conf' in data.columns else f'{keypoint}_vis'
                conf1 = data.loc[i, conf_col] if conf_col in data.columns else 1.0
                conf2 = data.loc[i+1, conf_col] if conf_col in data.columns else 1.0
                if conf1 < CONFIDENCE_THRESHOLD or conf2 < CONFIDENCE_THRESHOLD:
                    speeds[keypoint].append(np.nan)
                    signed_speeds_y[keypoint].append(np.nan)
                    continue
                pos1 = np.array([data.loc[i, f'{keypoint}_x'], data.loc[i, f'{keypoint}_y'], data.loc[i, f'{keypoint}_z']])
                pos2 = np.array([data.loc[i+1, f'{keypoint}_x'], data.loc[i+1, f'{keypoint}_y'], data.loc[i+1, f'{keypoint}_z']])
                distance = np.linalg.norm(pos2 - pos1)
                time_diff = (data.loc[i+1, 'timestamp_ms'] - data.loc[i, 'timestamp_ms']) / 1000  # in seconds
                speed = distance / time_diff if time_diff > 0 else 0
                speeds[keypoint].append(speed)
                
                # Signed y-velocity (negative if moving down, positive up)
                vel_y = (pos2[1] - pos1[1]) / time_diff if time_diff > 0 else 0
                signed_speeds_y[keypoint].append(vel_y)
            # For the last frame, append NaN if low confidence
            conf_col = f'{keypoint}_conf' if f'{keypoint}_conf' in data.columns else f'{keypoint}_vis'
            if len(data) == 0:
                conf_last = 0.0
            else:
                conf_last = data.iloc[-1][conf_col] if conf_col in data.columns else 1.0
            speeds[keypoint].append(0 if conf_last >= CONFIDENCE_THRESHOLD else np.nan)
            signed_speeds_y[keypoint].append(0 if conf_last >= CONFIDENCE_THRESHOLD else np.nan)
            
            # Calculate acceleration as change in speed / time, skip if NaN
            for i in range(len(speeds[keypoint]) - 1):
                if np.isnan(speeds[keypoint][i]) or np.isnan(speeds[keypoint][i+1]):
                    accelerations[keypoint].append(np.nan)
                    continue
                time_diff = (data.loc[i+1, 'timestamp_ms'] - data.loc[i, 'timestamp_ms']) / 1000
                acc = (speeds[keypoint][i+1] - speeds[keypoint][i]) / time_diff if time_diff > 0 else 0
                accelerations[keypoint].append(acc)
            accelerations[keypoint].append(np.nan)  # last
    
    # Smooth speeds, skip NaN
    for key in speeds:
        valid_mask = ~np.isnan(speeds[key])
        if np.any(valid_mask):
            smoothed = smooth_data(np.array(speeds[key])[valid_mask], sigma=2)
            speeds[key] = np.full(len(speeds[key]), np.nan)
            speeds[key][valid_mask] = smoothed
        signed_speeds_y[key] = np.array(signed_speeds_y[key])  # No smoothing for signed, but could add if needed
    
    return speeds, accelerations, signed_speeds_y

# Detect rep start, end, and max depth
def detect_rep_points(displacement):
    """
    Detect rep start, end, and max depth. Supports expected_reps for stricter single-rep detection.
    """
    tolerance = 0.05  # Tolerance for "near 0" displacement; adjust based on data scale
    import inspect
    frame = inspect.currentframe().f_back
    expected_reps = frame.f_locals.get('expected_reps', None)
    def _find_peaks(displacement, expected_reps=None):
        if expected_reps == 1:
            peaks, props = find_peaks(displacement, prominence=0.05)
            if len(peaks) == 0:
                max_depth_frame = np.argmax(displacement)
                peaks = [max_depth_frame]
            elif len(peaks) > 1:
                # Pick the peak with largest displacement
                max_disp = np.argmax(displacement[peaks])
                peaks = [peaks[max_disp]]
            return peaks
        else:
            peaks, _ = find_peaks(displacement, height=tolerance, distance=30)
            if len(peaks) == 0:
                max_depth_frame = np.argmax(displacement)
                peaks = [max_depth_frame]
            return peaks
    peaks = _find_peaks(displacement, expected_reps)
    reps = []
    prev_end = -1
    for peak in peaks:
        max_depth_frame = peak
        # Start frame: search backwards from max_depth for the last frame where displacement is near 0
        start_frame = None
        for i in range(max_depth_frame - 1, prev_end, -1):
            if abs(displacement.iloc[i]) < tolerance:
                start_frame = i
                break
        if start_frame is None:
            start_frame = prev_end + 1 if prev_end + 1 < max_depth_frame else max_depth_frame
        # End frame: search forwards from max_depth for the first frame where displacement is near 0
        end_frame = None
        for i in range(max_depth_frame, len(displacement)):
            if abs(displacement.iloc[i]) < tolerance:
                end_frame = i
                break
        if end_frame is None:
            end_frame = len(displacement) - 1
        reps.append({
            'start_frame': start_frame,
            'end_frame': end_frame,
            'max_depth_frame': max_depth_frame
        })
        prev_end = end_frame
    return reps

# --- Body metrics helpers ---
def read_body_metrics_from_csv(csv_path):
    """Read height and shoulder_width from CSV header comments."""
    import numpy as np
    height = np.nan
    shoulder_width = np.nan
    with open(csv_path, 'r') as f:
        for _ in range(2):
            line = f.readline()
            if line.startswith('# height='):
                try:
                    height = float(line.strip().split('=')[1])
                except Exception:
                    pass
            if line.startswith('# shoulder_width='):
                try:
                    shoulder_width = float(line.strip().split('=')[1])
                except Exception:
                    pass
    return height, shoulder_width

def normalize_signals(signals_dict, height):
    """Normalize all distance-based signals by height."""
    import numpy as np
    if not height or np.isnan(height) or height == 0:
        return signals_dict
    normed = {}
    for k, v in signals_dict.items():
        if any(x in k for x in ['_x', '_y', '_z', 'displacement', 'distance', 'speed', 'acceleration']):
            normed[k] = np.array(v) / height
        else:
            normed[k] = v
    return normed

# ======================= SIGNAL PROCESSING PIPELINE =======================
def process_signals(data, expected_reps=None):
    """
    Main signal processing pipeline: smooth, normalize, extract features, detect reps.
    
    Args:
        data: Input motion capture data
        expected_reps: Optional expected number of repetitions (for stricter detection)
    
    Returns:
        Processed data with features and rep information
    """
    rep_id = None  # Fix NameError: ensure rep_id is always defined
    # Smooth data
    for col in ['x', 'y', 'z']:
        for keypoint in [k for k in data.columns if col in k]:
            data[keypoint] = pd.to_numeric(data[keypoint], errors='coerce').astype(float)
            data[keypoint] = smooth_data(data[keypoint])
    
    # Estimate height dynamically based on shoulder-to-feet distance
    height = estimate_height(data)
    
    # Normalize coordinates based on height
    data = normalize_coordinates(data, height)
    
    # Extract joint angles (now with confidence filtering)
    angles = extract_joint_angles(data)
    
    # Calculate angular speeds (with NaN handling)
    angular_speeds = {}
    for angle_name in angles:
        angular_speeds[angle_name] = []
        for i in range(len(angles[angle_name]) - 1):
            if np.isnan(angles[angle_name][i]) or np.isnan(angles[angle_name][i+1]):
                angular_speeds[angle_name].append(np.nan)
                continue
            time_diff = (data.loc[i+1, 'timestamp_ms'] - data.loc[i, 'timestamp_ms']) / 1000
            ang_speed = (angles[angle_name][i+1] - angles[angle_name][i]) / time_diff if time_diff > 0 else 0
            angular_speeds[angle_name].append(ang_speed)
        angular_speeds[angle_name].append(np.nan)
    
    # Calculate speed and acceleration (now with confidence filtering)
    speeds, accelerations, signed_speeds_y = calculate_speed(data)
    
    # Calculate symmetry (now with confidence filtering)
    symmetry_scores = calculate_symmetry(data, angles)
    
    # Calculate displacement for rep detection
    left_elbow_y = data['left_elbow_y']
    right_elbow_y = data['right_elbow_y']
    elbow_y = (left_elbow_y + right_elbow_y) / 2
    if elbow_y.empty:
        raise ValueError("Input data has no frames: cannot compute displacement for rep detection.")
    displacement = elbow_y - elbow_y.iloc[0]
    # Detect rep points with expected_reps and rep_id
    reps = detect_rep_points(displacement)
    # if expected_reps is not None and len(reps) != expected_reps:
        # raise ValueError(f"Expected {expected_reps} rep(s), but detected {len(reps)} rep(s). Detected reps: {reps}")
    if rep_id is not None:
        if rep_id >= len(reps):
            raise ValueError(f"Requested rep_id {rep_id}, but only {len(reps)} reps detected.")
        reps = [reps[rep_id]]
    # Add per-rep metrics
    for idx, rep in enumerate(reps):
        rep['rep_id'] = idx
        rep['max_depth_value'] = displacement.iloc[rep['max_depth_frame']]
        rep['avg_speed_left_elbow'] = np.nanmean(signed_speeds_y['left_elbow'][rep['start_frame']:rep['end_frame']+1])
        rep['avg_speed_right_elbow'] = np.nanmean(signed_speeds_y['right_elbow'][rep['start_frame']:rep['end_frame']+1])
        rep['rep_duration_ms'] = (rep['end_frame'] - rep['start_frame']) * (data.loc[1, 'timestamp_ms'] - data.loc[0, 'timestamp_ms']) if len(data) > 1 else 0
    # Calculate rest periods between reps
    for i, rep in enumerate(reps):
        if i > 0:
            rest_duration_ms = data.loc[rep['start_frame'], 'timestamp_ms'] - data.loc[reps[i-1]['end_frame'], 'timestamp_ms']
            rep['rest_duration_before_ms'] = rest_duration_ms
        else:
            rep['rest_duration_before_ms'] = 0
    
    return {
        'angles': angles,
        'speeds': speeds,
        'accelerations': accelerations,
        'symmetry_scores': symmetry_scores,
        'angular_speeds': angular_speeds,
        'signed_speeds_y': signed_speeds_y,
        'reps': reps,
        'data': data
    }

# ======================= GROUND TRUTH PROFILE CALCULATION =======================
def calculate_ground_truth_profile(gt_csv_path):
    """
    Calculate averaged metrics across all reps in ground truth CSV.
    
    Args:
        gt_csv_path: Path to ground truth analyzed CSV
    
    Returns:
        Tuple of (average_signals_dict, reps_list, total_frame_count, metadata)
    """
    df = pd.read_csv(gt_csv_path)
    
    # Extract rep summary rows (those with rep_id in column)
    if 'rep_id' not in df.columns:
        raise ValueError("Ground truth CSV must have 'rep_id' column")
    
    # Find rep summary rows (they have non-NaN rep_id values and typically appear at end)
    # For now, assume all rows with valid data are frame rows, extract reps from data
    reps_info = []
    
    # Extract rep information: assume frames with same rep_id belong to same rep
    rep_ids = df['rep_id'].dropna().unique()
    
    signal_cols = [col for col in df.columns if col not in ['frame', 'timestamp_ms', 'rep_id', 
                   'rep_start_frame', 'rep_end_frame', 'max_depth_frame', 'max_depth_value',
                   'avg_speed_left_elbow', 'avg_speed_right_elbow', 'rep_duration_ms',
                   'rest_duration_before_ms']]
    
    # Average signals across all reps
    avg_signals = {}
    for col in signal_cols:
        if col in df.columns:
            valid_vals = df[col].dropna()
            if len(valid_vals) > 0:
                avg_signals[col] = np.mean(valid_vals)
    
    return avg_signals, reps_info, len(df), signal_cols

# ======================= COMPARE EXERCISES =======================
def compare_exercises(gt_csv_path, comparison_csv_path, output_path='pose_outputs/comparison_results.csv',
                      summary_path='pose_outputs/comparison_summary.csv', 
                      is_ground_truth_first=True):
    """
    Compare two exercise CSVs using ground truth as reference.
    
    Args:
        gt_csv_path: Path to ground truth analyzed CSV
        comparison_csv_path: Path to comparison analyzed CSV
        output_path: Path for detailed frame-by-frame comparison output
        summary_path: Path for per-rep summary
        is_ground_truth_first: If True, first CSV is GT; else second is GT
    
    Returns:
        Tuple of (detailed_df, summary_df)
    """
    df_gt = pd.read_csv(gt_csv_path)
    df_comp = pd.read_csv(comparison_csv_path)
    
    # Swap if needed
    if not is_ground_truth_first:
        df_gt, df_comp = df_comp, df_gt
    
    # Extract all signal columns (exclude metadata)
    metadata_cols = {'frame', 'timestamp_ms', 'rep_id', 'rep_start_frame', 'rep_end_frame', 
                     'max_depth_frame', 'max_depth_value', 'avg_speed_left_elbow', 'avg_speed_right_elbow',
                     'rep_duration_ms', 'rest_duration_before_ms'}
    
    signal_cols = [col for col in df_gt.columns if col not in metadata_cols and col in df_comp.columns]
    
    # Calculate ground truth averages
    gt_avg = {}
    for col in signal_cols:
        valid_vals = df_gt[col].dropna()
        if len(valid_vals) > 0:
            gt_avg[col] = np.mean(valid_vals)
        else:
            gt_avg[col] = np.nan
    
    # Extract reps from comparison CSV
    comp_rep_ids = df_comp['rep_id'].dropna().unique()
    
    # Build detailed comparison output
    detailed_rows = []
    summary_rows = []
    
    for rep_id in sorted(comp_rep_ids):
        rep_data = df_comp[df_comp['rep_id'] == rep_id].copy()
        
        if len(rep_data) == 0:
            continue
        
        rep_start_idx = rep_data.index[0]
        rep_end_idx = rep_data.index[-1]
        rep_frames = rep_end_idx - rep_start_idx + 1
        
        # Get GT average warped to this rep's duration
        gt_warped = warp_signals_to_duration(gt_avg, len(df_gt), rep_frames)
        
        flagged_frames = []
        joint_deviations = {}
        symmetry_deviations = {}
        
        # Compare each frame
        for local_frame_idx, (idx, row) in enumerate(rep_data.iterrows()):
            frame_annotations = {}
            
            for signal_name in signal_cols:
                if signal_name not in gt_avg or pd.isna(gt_avg[signal_name]):
                    continue
                
                gt_val = gt_warped.get(signal_name, [np.nan])[local_frame_idx] if signal_name in gt_warped else gt_avg[signal_name]
                actual_val = row[signal_name]
                
                if pd.isna(actual_val) or pd.isna(gt_val):
                    continue
                
                difference = actual_val - gt_val
                
                # Determine tolerance based on signal type
                tolerance = SIGNAL_TOLERANCES.get('angle', 5.0)  # default
                if '_speed' in signal_name:
                    tolerance = abs(gt_val * SIGNAL_TOLERANCES['speed'])
                elif '_acceleration' in signal_name:
                    tolerance = abs(gt_val * SIGNAL_TOLERANCES['acceleration'])
                elif 'symmetry' in signal_name:
                    tolerance = SIGNAL_TOLERANCES['symmetry']
                elif '_angular_speed' in signal_name:
                    tolerance = SIGNAL_TOLERANCES['angular_speed']
                
                # Check if exceeds tolerance
                if abs(difference) > tolerance:
                    flagged_frames.append(local_frame_idx)
                    
                    # Extract joint name
                    joint_name = signal_name.split('_')[0] + '_' + signal_name.split('_')[1] if '_' in signal_name else signal_name
                    
                    frame_annotations[signal_name] = {
                        'joint_name': joint_name,
                        'signal_name': signal_name,
                        'gt_value': gt_val,
                        'actual_value': actual_val,
                        'difference': difference
                    }
                    
                    # Track by joint or symmetry for scoring
                    if any(joint in signal_name for joint in JOINT_SIGNALS):
                        joint_deviations.setdefault(joint_name, []).append(abs(difference))
                    elif any(sym in signal_name for sym in SYMMETRY_SIGNALS):
                        symmetry_deviations.setdefault(signal_name, []).append(abs(difference))
            
            # Add row to detailed output with annotations
            row_output = row.copy()
            if frame_annotations:
                # Serialize annotations as JSON-like signal_name or separate columns
                for signal_name, annot in frame_annotations.items():
                    row_output[f'{signal_name}_annotation'] = f"{annot['joint_name']}|{annot['gt_value']:.4f}|{annot['actual_value']:.4f}|{annot['difference']:.4f}"
            
            detailed_rows.append(row_output)
        
        # Calculate form quality score
        total_flagged = len(set(flagged_frames))
        total_frames = rep_frames
        flagged_ratio = total_flagged / total_frames if total_frames > 0 else 0
        
        # Weight by joint vs symmetry
        joint_severity = np.mean(list(joint_deviations.values())) if joint_deviations else 0
        sym_severity = np.mean(list(symmetry_deviations.values())) if symmetry_deviations else 0
        
        form_quality = max(0, 100 * (1 - flagged_ratio * (0.5 + 0.5 * joint_severity)))
        symmetry_quality = max(0, 100 * (1 - flagged_ratio * (0.5 + 0.5 * sym_severity)))
        
        # Build summary row
        summary_row = {
            'rep_id': rep_id,
            'rep_frames': rep_frames,
            'flagged_frames': total_flagged,
            'flagged_ratio': flagged_ratio,
            'primary_joint_deviations': ', '.join([f"{k}:{v:.2f}" for k, v in sorted(joint_deviations.items(), key=lambda x: np.mean(x[1]), reverse=True)[:3]]),
            'form_quality_score': form_quality,
            'symmetry_quality_score': symmetry_quality,
            'overall_score': (form_quality * JOINT_WEIGHT + symmetry_quality * SYMMETRY_WEIGHT)
        }
        
        if 'rep_duration_ms' in rep_data.columns:
            rep_duration = rep_data['rep_duration_ms'].iloc[0]
            gt_avg_duration = df_gt['rep_duration_ms'].mean()
            summary_row['rep_duration_ms'] = rep_duration
            summary_row['rep_duration_diff_ms'] = rep_duration - gt_avg_duration
        
        summary_rows.append(summary_row)
    
    # Convert to DataFrames
    detailed_df = pd.DataFrame(detailed_rows)
    summary_df = pd.DataFrame(summary_rows)
    
    # Save outputs
    detailed_df.to_csv(output_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    
    # Visualization
    if HAS_MATPLOTLIB:
        visualize_comparison(df_gt, df_comp, signal_cols, gt_avg, comp_rep_ids)
    
    return detailed_df, summary_df

def visualize_comparison(df_gt, df_comp, signal_cols, gt_avg, rep_ids):
    """
    Visualize comparison with overlaid signals and deviation zones.
    """
    if len(signal_cols) == 0:
        return
    
    # Select key signals to visualize
    key_signals = [col for col in signal_cols if 'left_elbow' in col or 'right_elbow' in col or 
                   'left_knee' in col or 'elbow_angle_symmetry' in col][:4]
    
    if not key_signals:
        key_signals = signal_cols[:4]
    
    fig, axes = plt.subplots(len(key_signals), 1, figsize=(14, 4*len(key_signals)))
    if len(key_signals) == 1:
        axes = [axes]
    
    for signal_idx, signal_name in enumerate(key_signals):
        ax = axes[signal_idx]
        
        # Plot GT average
        gt_vals = df_gt[signal_name].dropna()
        ax.plot(range(len(gt_vals)), gt_vals, label='GT Average', color='green', linestyle='--', linewidth=2)
        
        # Plot comparison reps
        for rep_id in sorted(rep_ids):
            rep_data = df_comp[df_comp['rep_id'] == rep_id]
            if len(rep_data) > 0 and signal_name in rep_data.columns:
                rep_vals = rep_data[signal_name].values
                warped_rep = warp_signals_to_duration({signal_name: rep_vals}, len(rep_vals), len(gt_vals))
                ax.plot(range(len(gt_vals)), warped_rep[signal_name], label=f'Rep {int(rep_id)}', alpha=0.7)
        
        ax.set_title(f"Signal: {signal_name}")
        ax.set_xlabel("Normalized Frame")
        ax.set_ylabel("Value")
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('pose_outputs/comparison_visualization.png', dpi=100)
    if HAS_MATPLOTLIB:
        plt.close()
