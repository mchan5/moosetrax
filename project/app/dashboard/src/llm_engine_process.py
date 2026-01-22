import os
from dotenv import load_dotenv
from openai import OpenAI
import instructor
from pydantic import BaseModel, Field
from typing import List
from pathlib import Path

current_file = Path(__file__).resolve()
src_dir = current_file.parent  # .../src
dashboard_dir = src_dir.parent # .../dashboard

env_path = dashboard_dir / '.env'

# Load the file explicitly
load_dotenv(dotenv_path=env_path)

load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY is missing from .env file")

client = instructor.from_openai(
    OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.getenv("GEMINI_API_KEY")
    ),
    mode=instructor.Mode.JSON
)
ai_model = "gemini-2.5-flash"

# ai_model = "deepseek/deepseek-r1-0528:free"
# client = instructor.from_openai(
#     OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key=os.getenv("DEEPSEEK_API_KEY")
#     ),
#     mode=instructor.Mode.JSON
# )

headers = {
    "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
    "Content-Type": "application/json" # Common for JSON payloads
}

# Data Schemas
class RepetitionAnalysis(BaseModel):
    timestamp_start: float
    timestamp_end: float
    rep_id: int
    deviation_score: float
    primary_metric: str = Field(..., description="Clean name of the issue e.g. 'Knee Stability'")
    metric_value: str = Field(..., description="Specific numbers e.g. '145 deg' or 'N/A'")
    description: str = Field(..., description="A 1-sentence critique of what went wrong.")
    correction_cue: str = Field(..., description="A specific, actionable cue selected from the provided Cue Bank.")

class VideoAnalysis(BaseModel):
    video_id: str
    fps: int = 30
    comparison_metrics: List[RepetitionAnalysis]

# 3. GENERATION LOGIC
def generate_rep_analysis_json(rep_summaries: list, cue_bank: list) -> VideoAnalysis:
    
    prompt = f"""
    You are an expert Biomechanics AI Coach.
    I will provide raw data from a user's workout and a Bank of Coaching Cues.
    
    INPUT DATA KEYS:
    - "primary_metric_raw": The body part involved (e.g., 'Knee', 'Hip').
    - "metric_value_raw" or "all_errors": The technical details of the failure.

    CUE BANK (List of available advice):
    {cue_bank}

    YOUR GOAL:
    Convert the raw data into a clean JSON timeline and select the BEST cue.

    RULES:
    1. **Analysis:** - If `deviation_score` is high (near 1.0), the form is bad. Describe the specific error using the `all_errors` data.
       - Example description: "Knee angle collapsed to 145° instead of maintaining 162°."
    
    2. **Cue Selection (CRITICAL):**
       - Look at the "primary_metric_raw" and the specific error type.
       - SEARCH the `CUE BANK` above for the most relevant advice.
       - If the error is about "Knees", pick a cue like "Push knees outward."
       - If the error is about "Hips", pick a cue like "Squeeze glutes."
       - **Do not invent cues.** Try to stick to the style of the bank provided.

    3. **Metric Extraction:**
       - format `metric_value` cleanly. E.g. "145° vs 162°".

    INPUT DATA:
    {rep_summaries}
    """

    print("  Gemini is analyzing rep data & selecting cues...")

    response = client.chat.completions.create(
        model=ai_model, 
        response_model=VideoAnalysis,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    return response