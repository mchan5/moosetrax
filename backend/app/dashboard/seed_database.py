import os
import uuid
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Supabase keys missing from .env")

supabase: Client = create_client(url, key)

# Sample User ID
USER_ID = "76f963f6-4a5b-4248-bbe2-69122852a87b"

# Sample data to test
scenarios = [
    {
        "days_ago": 5,
        "score": 45,
        "level": "Beginner",
        "primary_fault": "Hip Sag",
        "summary": "Significant form breakdown. Core stability failed early in the set.",
        "strengths": ["Wrist Position"],
        "weaknesses": ["Severe Hip Sag", "Head Dropping"],
        "remedial": [
            {
                "name": "Modified Plank",
                "target_fault": "Hip Sag",
                "prescription": "3 x 30s",
                "adaptive_reasoning": "Building baseline core strength before standard pushups."
            }
        ]
    },
    {
        "days_ago": 4,
        "score": 60,
        "level": "Beginner",
        "primary_fault": "Core Instability",
        "summary": "Better alignment, but fatigue caused shaking (instability) halfway through.",
        "strengths": ["Depth", "Hand Placement"],
        "weaknesses": ["Core Instability"],
        "remedial": [
            {
                "name": "Deadbug",
                "target_fault": "Core Instability",
                "prescription": "3 x 12 reps",
                "adaptive_reasoning": "Low-impact core work to fix stability."
            }
        ]
    },
    {
        "days_ago": 2,
        "score": 78,
        "level": "Intermediate",
        "primary_fault": "Elbow Flare",
        "summary": "Solid foundation. Hips stayed up, but elbows are flaring out to 90 degrees.",
        "strengths": ["Neutral Spine", "Consistent Depth"],
        "weaknesses": ["Elbow Flare"],
        "remedial": [
            {
                "name": "Band-Resisted Pushup",
                "target_fault": "Elbow Flare",
                "prescription": "3 x 10 reps",
                "adaptive_reasoning": "The band forces elbows to tuck naturally."
            }
        ]
    },
    {
        "days_ago": 1,
        "score": 85,
        "level": "Intermediate",
        "primary_fault": "Tempo",
        "summary": "Excellent mechanics. Main issue now is rushing the downward phase.",
        "strengths": ["Elbow Tuck", "Core Stability", "Depth"],
        "weaknesses": ["Rushed Tempo"],
        "remedial": [
            {
                "name": "Tempo Pushups (3-1-1)",
                "target_fault": "Rushed Tempo",
                "prescription": "3 x 8 reps",
                "adaptive_reasoning": "Slowing down specifically to master control."
            }
        ]
    },
    {
        "days_ago": 0,
        "score": 92,
        "level": "Advanced",
        "primary_fault": "None",
        "summary": "Near perfect session. Great control, depth, and alignment throughout.",
        "strengths": ["Perfect Depth", "Stable Core", "Controlled Tempo"],
        "weaknesses": [],
        "remedial": [
            {
                "name": "Weighted Pushups",
                "target_fault": "None",
                "prescription": "3 x 10 reps",
                "adaptive_reasoning": "Form is mastered; time to increase load."
            }
        ]
    }
]

def seed_data():
    print(f"🌱 Seeding Supabase for User: {USER_ID}...")

    for s in scenarios:
        analysis_json = {
            "user_skill_level": s["level"],
            "personalized_summary": s["summary"],
            "strengths": s["strengths"],
            "weaknesses": s["weaknesses"],
            "remedial_plan": s["remedial"],
            "gamification": {
                "form_score": s["score"],
                "xp_earned": int(s["score"] * 1.2),
                "current_level_title": s["level"],
                "streak_bonus": True
            },
            # Empty list for timeline events is fine, but it must exist
            "timeline_events": [] 
        }

        # Construct  SQL Row
        row = {
            "user_id": USER_ID,
            "created_at": (datetime.now() - timedelta(days=s["days_ago"])).isoformat(),
            "form_score": s["score"],
            "primary_fault": s["primary_fault"],
            "analysis": analysis_json # Dumping JSON here
        }

        try:
            supabase.table("workout_sessions").insert(row).execute()
            print(f"Inserted: Score {s['score']} ({s['days_ago']} days ago)")
        except Exception as e:
            print(f"Error inserting row: {e}")

if __name__ == "__main__":
    seed_data()