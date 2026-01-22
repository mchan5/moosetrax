from dashboard.process_local_files import main as run_process_local_files 
from dashboard.single_video_analysis import main as run_single_video_analysis
from dashboard.dashboard_runner import main as run_dashboard_runner   


def run_pipeline(user_video_path): 

    if not run_process_local_files(): 
        print("Pipeline Stopped: Local File Processing Failed")
        return False

    if not run_single_video_analysis(user_video_path):
        print("Pipeline Stopped: Single Video Analysis Failed")
        return False

    if not run_dashboard_runner(): 
        print("Pipeline Stopped: Dashboard Runner Failed")
        return False

    print("Pipeline Completed Successfully!")
    return True

if __name__ == "__main__":
    run_pipeline(user_video_path="C:\\Users\\Happy\\Desktop\\uthacks\\trainer\\backend\\app\\uploads\\Screen Recording 2025-08-19 112615.mp4.mp4")

