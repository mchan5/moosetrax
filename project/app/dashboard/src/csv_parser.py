import pandas as pd 
import re

def parse_rep_data(csv_path, txt_path):
    """
    Reads the raw CSV/TXT file and condenses it into a Rep-by-Rep Summary for the LLM
    """

    df = pd.read_csv(csv_path) 
    fps = 30.0

    reps = []
    unique_rep_ids = df['rep_id'].unique()

    for r_id in unique_rep_ids: 
        rep_df = df[df['rep_id'] == r_id]

        if r_id == 0 and len(unique_rep_ids) > 1: 
            continue

        start_frame = rep_df['frame_absolute'].min()
        end_frame = rep_df['frame_absolute'].max()  
        duration_frames = len(rep_df)

        flag_cols = [c for c in df.columns if c.endswith('_flagged')]
        flag_counts = rep_df[flag_cols].sum().sort_values(ascending=False)

        top_issue_col = flag_counts.index[0]
        total_flags = flag_counts.iloc[0]

        deviation_score = round(total_flags / duration_frames, 2) 

        annotation_col = top_issue_col.replace('_flagged', '_annotation') 
        unique_notes = rep_df[annotation_col].dropna().unique().tolist()

        primary_metric_name = top_issue_col.replace('_flagged', '').replace('_', ' ').title()

        reps.append({
            "rep_id": int(r_id),
            "timestamp_start": round(start_frame / fps, 2),
            "timestamp_end": round(end_frame / fps, 2),
            "deviation_score": deviation_score,
            "primary_metric_raw": primary_metric_name,
            "metric_value_raw": unique_notes[0] if unique_notes else "N/A", # Grab first error example
            "all_errors": unique_notes[:3] # Send top 3 unique errors to LLM context
        })

        return reps