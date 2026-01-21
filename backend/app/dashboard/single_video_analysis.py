import json
import os 
from dotenv import load_dotenv
from .src.llm_engine import generate_analysis_script
from .src.video_overlay import render_video 
from .src.db_connector import save_session_to_db
from .src.schemas import AnalysisResult
from .src.video_overlay import render_video

load_dotenv() 

def main(user_video_path): 
    # Loading Data 
    print("Loading metrics...") 
    base_dir = os.path.dirname(os.path.abspath(__file__))
    metrics_json = os.path.join(base_dir, "data", "final_rep_analysis.json")
    with open(metrics_json, "r") as f: 
        metrics_data = f.read() 

    cue_bank = os.path.join(base_dir, "config", "cue_bank.json")
    with open(cue_bank, "r") as f: 
        cue_bank = f.read() 

    # Get LLM to fill out output
    print("Analyzing form and generating script...") 
    analysis_result = generate_analysis_script(metrics_data, cue_bank)  

    # Save the result as the final JSON Script 
    final_analysis = os.path.join(base_dir, "data", "final_analysis.json")
    output_filename = "final_analysis.json" 
    with open(final_analysis, "w") as f: 
        f.write(analysis_result.model_dump_json(indent=2))
    
    print(f"Analysis Complete, saved to {final_analysis}")
    print(f"Diagnosed Skill Level: {analysis_result.user_skill_level}")
    
    
    # Define paths
    # If no input video, create a black video test.
    raw_video = user_video_path 

    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "data", "final_analysis.json")
    # json_script = "data/final_rep_analysis.json"
    final_video = os.path.join(base_dir, "data", "annotated_output.mp4")

    render_video(raw_video, file_path, final_video)

    with open(file_path, "r") as f: 
        data = json.load(f)

    print("\n--- Saving to Cloud ---")
    try: 
        save_session_to_db(AnalysisResult(**data), video_name="demo")
    except Exception as e: 
        print(f" Database Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()