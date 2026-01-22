import os
from supabase import create_client, Client
from .schemas import AnalysisResult

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Missing Supabase credentials in .env file")
    return create_client(url, key)

def get_or_create_user(username: str = "demo_user"):
    """
    Ensures a user exists in the DB so we have an ID to attach sessions to.
    """
    sb = get_supabase_client()
    
    # 1. Try to find the user
    response = sb.table("users").select("id").eq("username", username).execute()
    
    if response.data:
        return response.data[0]['id']
    
    # 2. If not found, create them
    print(f"[DB] Creating new user: {username}...")
    new_user = sb.table("users").insert({"username": username}).execute()
    return new_user.data[0]['id']

def save_session_to_db(analysis: AnalysisResult, video_name: str = "upload_01.mp4"):
    """
    Saves the full AI analysis into Supabase using the exact SQL columns provided.
    """
    sb = get_supabase_client()
    
    # 1. Get the User ID 
    user_id = get_or_create_user("demo_user")
    
    print(f"[DB] Saving session for user {user_id}...")

    # 2. Insert the Session Summary
    session_payload = {
        "user_id": user_id,
        "video_name": video_name,
        "general_summary": analysis.general_summary,
        # Maps Python 'user_skill_level' -> SQL 'skill_level_snapshot'
        "skill_level_snapshot": analysis.user_skill_level
    }
    
    session_res = sb.table("sessions").insert(session_payload).execute()
    session_id = session_res.data[0]['id']

    # 3. Insert the Timeline Events
    events_payload = []
    for event in analysis.timeline_events:
        events_payload.append({
            "session_id": session_id,
            
            "timestamp_start": event.start_time,
            "timestamp_end":   event.end_time,

            "overlay_text":    event.overlay_text,
            "correction_cue":  event.correction_cue, 
            "status_colour":   event.status_color
        })
    
    if events_payload:
        # Saving to table 'feedback_events'
        sb.table("feedback_events").insert(events_payload).execute()
    
    # 4. Update the User's overall profile
    sb.table("users").update({"skill_level": analysis.user_skill_level}).eq("id", user_id).execute()

    print("[DB] Saved successfully to Supabase!")