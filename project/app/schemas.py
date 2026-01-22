from pydantic import BaseModel

#Request schemas
class ExerciseRequest(BaseModel):
    exercise: str

class UploadRequest(BaseModel):
    video_path: str

class AnalyzeRequest(BaseModel):
    text: str

#Response schemas
class AnalyzeResponse(BaseModel):
    video_path: str

class SummaryResponse(BaseModel):
    summary: str
