import os 
from dotenv import load_dotenv
from supabase import create_client, Client 
from .schemas import AnalysisResult

load_dotenv() 

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
sb = create_client(url, key)

def get_or_create_user(username: str = "demo_user"):
    response = sb.table("users").select("id").eq("username", username).execute()
    
    if response.data:
        return response.data[0]['id']
    
    print(f"[DB] Creating new user: {username}...")
    new_user = sb.table("users").insert({"username": username}).execute()
    return new_user.data[0]['id']

def fetch_user_history(user_id: str): 
    """
    Connects to Supabase and fetches history 
    """

    try: 
        response = sb.table("workout_sessions") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute()
        data = response.data

        if not data: 
            print(f"No history found for user {user_id}")
            return []

        print(f"Successfully fetched {len(data)} sessions from Supabase. ")
        return data

    except Exception as e: 
        print (f"Database Error: {e}")
        return []
    
def save_session_to_db(analysis: AnalysisResult, video_name: str = "processed_video.mp4"):
    """
    Saves the session into the 'workout_sessions' table.
    Stores the full AI analysis in the 'analysis' JSONB column.
    """
    
    # Get User
    user_id = get_or_create_user("demo_user")
    print(f"[DB] Saving session for user {user_id}...")

    # Convert Pydantic Object to Dict
    analysis_json = analysis.model_dump() 
    
    # analysis_json["annotated_video_filename"] = video_name

    # Prepare the SQL Row
    session_payload = {
        "user_id": user_id,
        "form_score": analysis.gamification.form_score,
        "primary_fault": analysis.weaknesses[0] if analysis.weaknesses else "None",
        "analysis": analysis_json,
        # "annotated_video_filename": video_name
    }

    try:
        response = sb.table("workout_sessions").insert(session_payload).execute()
        
        if response.data:
            session_id = response.data[0]['session_id']
            print(f"[DB] Session Saved! ID: {session_id}")
            return session_id
        else:
            print("[DB] Insert failed: No data returned.")
            return None

    except Exception as e:
        print(f"[DB] Database Error: {e}")
        return None