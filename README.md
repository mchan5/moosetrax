# Multi-Rep Exercise Analysis System - Moosetrax

**This project was inspired by many failed New Year's Resolutions of working out. It targets beginner athletes, by critiquing their form, recommending exercises depending on their performance and an inferred skill level, and improves retention to build strong habits.**
  
## Key Features
### Multi-Rep Support
-  Automatic detection of multiple reps
-  Each rep gets unique `rep_id` (0, 1, 2, ...)
-  Individual max_depth_frame per rep
-  Rest periods calculated between reps

### Ground-Truth Comparison
-  Dynamic time-warping of GT signals
-  Rep duration difference tracked
-  Tolerance-based deviation flagging
-  Metric-only annotations for LLM

### Comprehensive Analysis
-  150+ signals per frame (angles, speeds, symmetries)
-  33 keypoints tracked
-  8 joint angles extracted
-  5 symmetry scores calculated

### Smart Scoring
-  Form quality: 70% weight on joints
-  Symmetry quality: 30% weight
-  Combined overall score: 0-100%
-  Primary deviations identified (top 3)
---

## Acknowledgements
This project was developed along with three other people, who are listed as contributors to this project. My contributions included an PostgreSQL database to store user's exercise history and performance, and prompting an LLM to provide adaptive recommendations using this history. 

