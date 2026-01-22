import os 
from dotenv import load_dotenv
import instructor 
from openai import OpenAI 
from .schemas import AnalysisResult 
from pathlib import Path 

script_dir = Path(__file__).resolve().parent

env_path = script_dir.parent / '.env'

load_dotenv(dotenv_path=env_path)

# Initialize the client with Instructor patches

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing. Check .env file.")

# # 3. Setup Client
client = instructor.from_openai(
    OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=api_key
    ),
    mode=instructor.Mode.JSON
)
ai_key = "gemini-2.5-flash"
# client = instructor.from_openai(
#     OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key=os.getenv("DEEPSEEK_API_KEY")
#     ),
#     mode=instructor.Mode.JSON
# )
# ai_key = "deepseek/deepseek-r1-0528:free"

def generate_analysis_script(metrics_json: str, cue_bank_text: str) -> AnalysisResult: 
    """
    Converts raw metrics to structured Analysis output for the website to use.
    """

    response = client.chat.completions.create( 
        model=ai_key, 
        response_model=AnalysisResult, 
        messages=[
            {
                "role": "system", 
                "content": (
                    "You are an expert biomechanics and fitness coach. " 
                    "1. Analyze the input metrics and timestamps. " 
                    "2. Determine the user's skill level (Beginner=High deviation, Advanced=Low deviation). "
                    "3. Create a timeline of feedback events. " 
                    "4. For each event, write a two sentence-long text for the video overlay mentioning the problem and how they could improve, and DETAILED text for the website."
                    "5. TAILOR THE TONE: Encouraging/Simple for Beginners; Technical/Direct for Advanced."
                )
            }, 
            {
                "role": "user", 
                "content": f"""
                METRICS DATA: 
                {metrics_json}

                GUIDELINES / CUE BANK: 
                {cue_bank_text}
                """
            }
        ]
    )
    return response