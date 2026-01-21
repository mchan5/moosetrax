import os
import instructor
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta
from typing import List, Dict
from .schemas import WeeklyReport

# Load Env vars
load_dotenv() 

# Check for Key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing. Check .env file.")

# Setup Client
client = instructor.from_openai(
    OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=api_key
    ),
    mode=instructor.Mode.JSON
)
ai_model = "gemini-2.5-flash"

# client = instructor.from_openai(
#     OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key=os.getenv("DEEPSEEK_API_KEY")
#     ),
#     mode=instructor.Mode.JSON
# )
# ai_model = "deepseek/deepseek-r1-0528:free"

def calculate_streak(dates: List[str]) -> int:
    """Helper to calculate consecutive days active."""
    if not dates:
        return 0
    
    # Convert strings to date objects and sort unique dates
    dt_objs = sorted(list(set([datetime.strptime(d, "%Y-%m-%d").date() for d in dates])))
    
    streak = 1
    # Check backwards from the most recent date
    for i in range(len(dt_objs) - 1, 0, -1):
        if (dt_objs[i] - dt_objs[i-1]).days == 1:
            streak += 1
        else:
            break
    return streak

def generate_weekly_report(past_sessions: List[dict]) -> WeeklyReport: 
    """
    Takes a list of raw JSON DB entries and generates a Meta-Analysis.
    """

    print("Computing stats")
    
    # Count total exercises
    total_exercises = len(past_sessions)
    
    # Calculate Streak
    dates = [s.get('created_at', '2024-01-01')[:10] for s in past_sessions if 'created_at' in s]
    streak = calculate_streak(dates)
    
    # Find best workout (one with highest score)
    if not past_sessions:
        best_id = "N/A"
        best_score = 0
    else:
        best_session = max(past_sessions, key=lambda x: x.get('form_score', 0))
        best_id = best_session.get('session_id', 'Unknown')
        best_score = best_session.get('form_score', 0)

    print("Passing through LLM")
    
    context_text = f"""
    HISTORY SUMMARY:
    - Total Sessions: {total_exercises}
    - Calculated Streak: {streak} days
    - Best Session ID: {best_id} (Score: {best_score})
    
    PAST SESSION DATA:
    {past_sessions}
    """

    response = client.chat.completions.create(
        model=ai_model, 
        response_model=WeeklyReport,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a Head Coach analyzing a week of training. "
                    "1. SUMMARY: Break down performance into Arms, Legs, and Core. "
                    "2. RECS: Suggest exercises based on Frequency (what they love) and Weakness (what they failed). "
                    "3. VERIFY: Use the provided math for Streak and Totals. "
                    "4. BEST WORKOUT: Explain WHY the session with the highest score was the best."
                )
            },
            {
                "role": "user",
                "content": context_text
            }
        ]
    )
    
    # Force the Python-calculated math into the object
    response.current_streak_days = streak
    response.total_exercises_completed = total_exercises
    
    return response