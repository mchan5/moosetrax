from fastapi import APIRouter
from .schemas import AnalyzeRequest, AnalyzeResponse
from .services import analyze_text

router = APIRouter(prefix="/api")  # <-- this defines the router

@router.get("/ping")
def ping():
    return {"message": "pong"}

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    return analyze_text(req.text)
