from pydantic import BaseModel, Field
from typing import List, Literal

# Basic Analysis Schemas ---

class RemedialExercise(BaseModel):
    name: str = Field(..., description="Name of the exercise.")
    target_fault: str = Field(..., description="The error this exercise fixes.")
    prescription: str = Field(..., description="Sets and Reps.")
    adaptive_reasoning: str = Field(..., description="Why this fits the user's profile.")

class GamificationStats(BaseModel):
    form_score: int = Field(..., description="0-100 score based on biomechanics.")
    xp_earned: int = Field(..., description="Points for consistency and improvement.")
    current_level_title: str = Field(..., description="E.g., 'Stability Rookie'.")
    streak_bonus: bool = Field(..., description="True if they got extra XP.")

class VideoEvent(BaseModel):
    start_time: float
    end_time: float
    overlay_text: str = Field(..., max_length=25)
    detailed_explanation: str
    correction_cue: Literal['weakness', 'strength'] # str = Field(..., description="Either 'strength' or 'weakness'")
    status_color: Literal["green", "red", "yellow"]

# class VideoEvent(BaseModel): 
#     start_time: float = Field(..., description="Start time of Event")
#     end_time: float = Field(..., description="End time of Event") 
#     overlay_text : str=Field(..., max_length=50, description="Text to annotate over video")
#     detailed_explanation: str  = Field(..., description="Full sentence explanation")
#     correction_cue: str = Field(..., description="Specific cue to fix the problem") 
#     status_color: Literal["green", "red", "yellow"]

# class AnalysisResult(BaseModel): 
#     user_skill_level: Literal["Beginner", "Intermediate", "Advanced"] = Field(..., description="Infered skill level")
#     general_summary: str = Field(..., description = "A holistic view across the whole video")
#     timeline_events: List[VideoEvent] = Field(..., description="List of events and descriptions")

class AnalysisResult(BaseModel):
    user_skill_level: Literal["Beginner", "Intermediate", "Advanced"]
    general_summary: str
    gamification: GamificationStats
    strengths: List[str]
    weaknesses: List[str]
    remedial_plan: List[RemedialExercise]
    timeline_events: List[VideoEvent]
    annotated_video_filename: str

# Weekly Report Schemas ---

class BodyPartSummary(BaseModel):
    arms_analysis: str = Field(..., description="Summary of arm stability, strength, and form trends.")
    legs_analysis: str = Field(..., description="Summary of leg drive, stability, and stance trends.")
    core_analysis: str = Field(..., description="Summary of midline stability and bracing trends.")

class FutureRecommendation(BaseModel):
    exercise_name: str
    reasoning: str = Field(..., description="Why chosen: 'High Frequency', 'Fixes Weakness', etc.")
    expected_benefit: str

class WeeklyReport(BaseModel):
    body_part_breakdown: BodyPartSummary
    
    recommended_plan: List[FutureRecommendation]

    current_streak_days: int
    total_exercises_completed: int
    best_workout_id: str
    best_workout_reason: str