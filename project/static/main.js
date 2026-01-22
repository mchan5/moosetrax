let selectedExercise = "";
let videoFile = null;

const exerciseSelect = document.getElementById("exerciseSelect");
const videoInput = document.getElementById("videoInput");
const videoContainer = document.getElementById("videoContainer");
const output = document.getElementById("output");
const uploadBtn = document.getElementById("uploadBtn");
const dashboardBtn = document.getElementById("dashboardBtn");
const analyzeBtn = document.getElementById("analyzeBtn");

// Dropdown selection
exerciseSelect.addEventListener("change", (e) => {
  selectedExercise = e.target.value;
});

// Dashboard button click → navigate to dashboard
dashboardBtn.addEventListener("click", () => {
  window.location.href = "/dashboard.html";
});

// Upload button click → open file picker
uploadBtn.addEventListener("click", () => {
  videoInput.click();
});

// Video selection → preview + upload to backend
videoInput.addEventListener("change", async (e) => {
  videoFile = e.target.files[0];
  if (!videoFile) return;

  // 1️⃣ Show preview in browser
  const videoUrl = URL.createObjectURL(videoFile);
  videoContainer.innerHTML = `<video src="${videoUrl}" controls></video>`;

  // 2️⃣ Send file to backend for saving
  const formData = new FormData();
  formData.append("file", videoFile);

  try {
    const res = await fetch("/api/save-video", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    output.textContent = `Video saved as: ${data.filename}`;
  } catch (err) {
    output.textContent = "Error saving video: " + err;
  }
});

// Analyze button click
analyzeBtn.addEventListener("click", async () => {
  if (!videoFile || !selectedExercise) {
    output.textContent = "Please select an exercise and upload a video first";
    return;
  }

  // Show "Analyzing..." message
  output.textContent = "Analyzing...";

  const formData = new FormData();
  formData.append("file", videoFile);
  formData.append("exercise", selectedExercise);

  try {
    const res = await fetch("/api/analyze-video", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    console.log("Analyze response:", data);
    
    // Display the general_summary from final_analysis.json
    if (data.general_summary) {
      output.textContent = data.general_summary;
    } else {
      output.textContent = JSON.stringify(data, null, 2);
    }
    
    // Replace video with annotated_output.mp4 if available
    if (data.annotated_video_url) {
      console.log("Loading annotated video:", data.annotated_video_url);
      const video = document.createElement("video");
      video.src = data.annotated_video_url;
      video.controls = true;
      video.style.width = "100%";
      video.style.height = "100%";
      video.style.display = "block";
      video.style.objectFit = "contain";
      video.style.backgroundColor = "#000";
      
      // Add event listeners for debugging
      video.addEventListener("loadstart", () => console.log("Video: loadstart"));
      video.addEventListener("loadedmetadata", () => console.log("Video: loadedmetadata, duration:", video.duration));
      video.addEventListener("canplay", () => console.log("Video: canplay"));
      video.addEventListener("play", () => console.log("Video: play"));
      video.addEventListener("error", (e) => console.error("Video error:", e.target.error));
      
      videoContainer.innerHTML = "";
      videoContainer.appendChild(video);
      console.log("Video element created and appended, container dims:", videoContainer.offsetWidth, "x", videoContainer.offsetHeight);
      
      // Force load
      video.load();
      console.log("Video load() called");
    } else {
      console.warn("No annotated video URL in response");
    }
  } catch (err) {
    output.textContent = "Error analyzing video: " + err;
    console.error("Error during analysis:", err);
  }
});
