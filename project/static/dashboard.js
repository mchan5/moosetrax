// Load last uploaded video if element exists
const videoElement = document.getElementById("dashboardVideo");
if (videoElement) {
  const filename = localStorage.getItem("lastVideo");
  if (filename) {
    videoElement.src = `/uploads/${filename}`;
  } else {
    videoElement.style.display = "none";
  }
}

// Load Arms, Legs, and Core analysis into cards when page loads
async function loadBodyPartAnalysis() {
  try {
    const res = await fetch("/api/weekly-dashboard");
    const data = await res.json();
    
    // Load Arms analysis into first card
    const armsCard = document.getElementById("armsCard");
    if (armsCard && data.body_part_breakdown && data.body_part_breakdown.arms_analysis) {
      armsCard.innerHTML = `<h3>Arms</h3><p>${data.body_part_breakdown.arms_analysis}</p>`;
    }
    
    // Load Legs analysis into second card
    const legsCard = document.getElementById("legsCard");
    if (legsCard && data.body_part_breakdown && data.body_part_breakdown.legs_analysis) {
      legsCard.innerHTML = `<h3>Legs</h3><p>${data.body_part_breakdown.legs_analysis}</p>`;
    }
    
    // Load Core analysis into third card
    const coreCard = document.getElementById("coreCard");
    if (coreCard && data.body_part_breakdown && data.body_part_breakdown.core_analysis) {
      coreCard.innerHTML = `<h3>Core</h3><p>${data.body_part_breakdown.core_analysis}</p>`;
    }
    
    // Load Recommended Exercises
    const recommendationsSection = document.getElementById("recommendationsSection");
    if (recommendationsSection && data.recommended_plan && Array.isArray(data.recommended_plan)) {
      let html = `<h3>Recommended Exercises</h3><ul>`;
      data.recommended_plan.forEach(plan => {
        html += `<li><strong>${plan.exercise_name} - ${plan.reasoning}</strong><br><em>${plan.expected_benefit}</em></li>`;
      });
      html += `</ul>`;
      recommendationsSection.innerHTML = html;
    }
  } catch (err) {
    console.error("Error loading body part analysis:", err);
  }
}

// Add refresh button click handler
const refreshBtn = document.getElementById("refreshBtn");
if (refreshBtn) {
  refreshBtn.addEventListener("click", loadBodyPartAnalysis);
}

// Wait for DOM to be ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", loadBodyPartAnalysis);
} else {
  loadBodyPartAnalysis();
}
