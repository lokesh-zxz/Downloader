// Initialize Lucide icons
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  checkFFmpegStatus();
});

// App State
let currentVideoData = null;
let selectedResolution = null;
let activePollInterval = null;

// DOM Elements
const videoUrlInput = document.getElementById("videoUrl");
const fetchForm = document.getElementById("fetchForm");
const fetchBtn = document.getElementById("fetchBtn");
const fetchBtnText = document.getElementById("fetchBtnText");
const fetchBtnIcon = document.getElementById("fetchBtnIcon");
const fetchSpinner = document.getElementById("fetchSpinner");
const pasteBtn = document.getElementById("pasteBtn");

const loadingCard = document.getElementById("loadingCard");
const resultCard = document.getElementById("resultCard");
const errorAlert = document.getElementById("errorAlert");
const errorMessage = document.getElementById("errorMessage");
const closeErrorBtn = document.getElementById("closeErrorBtn");

const videoThumb = document.getElementById("videoThumb");
const videoTitle = document.getElementById("videoTitle");
const videoUploader = document.getElementById("videoUploader");
const videoViews = document.getElementById("videoViews");
const videoDuration = document.getElementById("videoDuration");
const badge4k = document.getElementById("badge4k");
const resolutionGrid = document.getElementById("resolutionGrid");

const startDownloadBtn = document.getElementById("startDownloadBtn");
const startDownloadBtnText = document.getElementById("startDownloadBtnText");

const progressCard = document.getElementById("progressCard");
const progressPercent = document.getElementById("progressPercent");
const progressBar = document.getElementById("progressBar");
const progressStage = document.getElementById("progressStage");
const statSpeed = document.getElementById("statSpeed");
const statEta = document.getElementById("statEta");
const downloadReadyNotice = document.getElementById("downloadReadyNotice");
const manualDownloadLink = document.getElementById("manualDownloadLink");

const ffmpegStatusBtn = document.getElementById("ffmpegStatusBtn");
const ffmpegModal = document.getElementById("ffmpegModal");
const closeModalBtn = document.getElementById("closeModalBtn");
const modalGotItBtn = document.getElementById("modalGotItBtn");
const copyCmdBtn = document.getElementById("copyCmdBtn");
const copyText = document.getElementById("copyText");

// Check FFmpeg status on startup
async function checkFFmpegStatus() {
  try {
    const res = await fetch("/api/system-status");
    const data = await res.json();
    if (data.installed) {
      ffmpegStatusBtn.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all duration-200 bg-emerald-950/60 border-emerald-500/40 text-emerald-300 hover:border-emerald-400";
      ffmpegStatusBtn.innerHTML = `
        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
        <span>FFmpeg Ready (4K Merging Active)</span>
      `;
    } else {
      ffmpegStatusBtn.className = "flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all duration-200 bg-amber-950/60 border-amber-500/40 text-amber-300 hover:border-amber-400 cursor-pointer";
      ffmpegStatusBtn.innerHTML = `
        <span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
        <span>FFmpeg Not Detected (Click to Setup)</span>
      `;
      ffmpegStatusBtn.onclick = () => ffmpegModal.classList.remove("hidden");
    }
  } catch (err) {
    console.error("FFmpeg check failed:", err);
  }
}

// Modal controls
if (closeModalBtn) closeModalBtn.onclick = () => ffmpegModal.classList.add("hidden");
if (modalGotItBtn) modalGotItBtn.onclick = () => ffmpegModal.classList.add("hidden");
if (ffmpegModal) {
  ffmpegModal.onclick = (e) => {
    if (e.target === ffmpegModal) ffmpegModal.classList.add("hidden");
  };
}

if (copyCmdBtn) {
  copyCmdBtn.onclick = () => {
    const cmd = document.getElementById("cmdWin").innerText;
    navigator.clipboard.writeText(cmd).then(() => {
      copyText.innerText = "Copied!";
      setTimeout(() => { copyText.innerText = "Copy"; }, 2000);
    });
  };
}

// Clipboard Paste
if (pasteBtn) {
  pasteBtn.onclick = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        videoUrlInput.value = text;
        triggerFetch();
      }
    } catch (e) {
      videoUrlInput.focus();
    }
  };
}

// Sample links
document.querySelectorAll(".sample-link").forEach(btn => {
  btn.onclick = () => {
    videoUrlInput.value = btn.dataset.url;
    triggerFetch();
  };
});

// Close error
if (closeErrorBtn) {
  closeErrorBtn.onclick = () => errorAlert.classList.add("hidden");
}

function showError(msg) {
  errorMessage.innerText = msg;
  errorAlert.classList.remove("hidden");
  loadingCard.classList.add("hidden");
  if (window.lucide) lucide.createIcons();
}

function hideError() {
  errorAlert.classList.add("hidden");
}

// Form Submission
fetchForm.onsubmit = (e) => {
  e.preventDefault();
  triggerFetch();
};

async function triggerFetch() {
  const url = videoUrlInput.value.trim();
  if (!url) return;

  hideError();
  resultCard.classList.add("hidden");
  progressCard.classList.add("hidden");
  if (activePollInterval) clearInterval(activePollInterval);

  // Set loading state
  fetchBtn.disabled = true;
  fetchBtnText.innerText = "Fetching...";
  fetchBtnIcon.classList.add("hidden");
  fetchSpinner.classList.remove("hidden");
  loadingCard.classList.remove("hidden");

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Failed to extract video information.");
    }

    currentVideoData = data;
    renderVideoMetadata(data);
  } catch (err) {
    showError(err.message || "Failed to connect to backend server.");
  } finally {
    fetchBtn.disabled = false;
    fetchBtnText.innerText = "Fetch Video";
    fetchBtnIcon.classList.remove("hidden");
    fetchSpinner.classList.add("hidden");
    loadingCard.classList.add("hidden");
  }
}

// Render Video Details
function renderVideoMetadata(data) {
  videoThumb.src = data.thumbnail || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop&q=60";
  videoTitle.innerText = data.title;
  videoUploader.querySelector("span").innerText = data.uploader;
  videoViews.querySelector("span").innerText = `${data.view_count_str} views`;
  videoDuration.innerText = data.duration_str;

  if (data.has_4k) {
    badge4k.classList.remove("hidden");
  } else {
    badge4k.classList.add("hidden");
  }

  // Populate Resolutions
  resolutionGrid.innerHTML = "";
  const resolutions = data.resolutions || [];

  // Default selection: pick 2160p if available, else 1080p, else first available
  selectedResolution = resolutions.find(r => r.height === 2160 && r.is_available)
    || resolutions.find(r => r.height === 1080 && r.is_available)
    || resolutions.find(r => r.is_available)
    || resolutions[0];

  resolutions.forEach((res, idx) => {
    const isSelected = selectedResolution && (selectedResolution.height === res.height && selectedResolution.type === res.type);
    const card = document.createElement("div");
    card.className = `resolution-card p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
      isSelected ? "selected border-brand-500 bg-brand-500/10" : "border-white/10 bg-slate-900/60 hover:border-white/20"
    } ${!res.is_available ? "opacity-50" : ""}`;

    // Resolution badge style
    let badgeClass = "bg-slate-800 text-slate-300 border-slate-700";
    if (res.is_4k) badgeClass = "bg-gradient-to-r from-amber-500/20 to-purple-500/20 text-amber-300 border-amber-500/30";
    else if (res.height === 1440) badgeClass = "bg-cyan-500/20 text-cyan-300 border-cyan-500/30";
    else if (res.height === 1080) badgeClass = "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";

    card.innerHTML = `
      <div class="flex items-center space-x-3">
        <div class="w-4 h-4 rounded-full border flex items-center justify-center ${isSelected ? 'border-brand-500 bg-brand-500' : 'border-slate-600'}">
          ${isSelected ? '<div class="w-1.5 h-1.5 rounded-full bg-white"></div>' : ''}
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <span class="text-xs sm:text-sm font-bold text-white">${res.name}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold border ${badgeClass}">${res.badge}</span>
          </div>
          <span class="text-[11px] text-slate-400 font-mono">${res.fps} &bull; ${res.estimated_size}</span>
        </div>
      </div>
      <div>
        ${res.is_4k ? '<span class="text-[10px] font-bold text-amber-400 tracking-wider">ULTRA HD</span>' : ''}
      </div>
    `;

    card.onclick = () => {
      selectedResolution = res;
      renderVideoMetadata(data); // Re-render selection highlight
    };

    resolutionGrid.appendChild(card);
  });

  updateDownloadBtnText();
  resultCard.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();
}

function updateDownloadBtnText() {
  if (!selectedResolution) return;
  if (selectedResolution.type === "audio") {
    startDownloadBtnText.innerText = "Download MP3 Audio (Lossless Extraction)";
  } else if (selectedResolution.is_4k) {
    startDownloadBtnText.innerText = "Download 4K Ultra HD (2160p) with Merged Audio";
  } else {
    startDownloadBtnText.innerText = `Download ${selectedResolution.badge} MP4`;
  }
}

// Start Download
startDownloadBtn.onclick = async () => {
  if (!currentVideoData || !selectedResolution) return;

  hideError();
  progressCard.classList.remove("hidden");
  downloadReadyNotice.classList.add("hidden");
  progressBar.style.width = "5%";
  progressPercent.innerText = "0%";
  progressStage.innerText = "Initializing 4K merger task...";
  statSpeed.innerText = "--";
  statEta.innerText = "--";

  // Scroll to progress
  progressCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

  try {
    startDownloadBtn.disabled = true;
    startDownloadBtn.classList.add("opacity-50", "cursor-not-allowed");

    const payload = {
      url: currentVideoData.webpage_url || videoUrlInput.value.trim(),
      height: selectedResolution.height,
      is_audio: selectedResolution.type === "audio",
    };

    const res = await fetch("/api/download/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to start download task.");
    }

    const taskId = data.task_id;
    pollTaskStatus(taskId);

  } catch (err) {
    showError(err.message || "Failed to start download.");
    startDownloadBtn.disabled = false;
    startDownloadBtn.classList.remove("opacity-50", "cursor-not-allowed");
    progressCard.classList.add("hidden");
  }
};

// Poll active download task
function pollTaskStatus(taskId) {
  if (activePollInterval) clearInterval(activePollInterval);

  activePollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/download/status/${taskId}`);
      if (!res.ok) {
        clearInterval(activePollInterval);
        throw new Error("Download task not found or timed out.");
      }

      const task = await res.json();

      if (task.status === "downloading" || task.status === "starting") {
        progressBar.style.width = `${Math.max(5, task.percent || 10)}%`;
        progressPercent.innerText = `${task.percent || 0}%`;
        progressStage.innerText = task.stage || "Downloading streams...";
        statSpeed.innerText = task.speed || "Calculating...";
        statEta.innerText = task.eta || "Calculating...";
      } else if (task.status === "processing") {
        progressBar.style.width = "99%";
        progressPercent.innerText = "99%";
        progressStage.innerText = task.stage || "Merging 4K video & audio with FFmpeg...";
        statSpeed.innerText = "FFmpeg Active";
        statEta.innerText = "Finishing";
      } else if (task.status === "completed") {
        clearInterval(activePollInterval);
        progressBar.style.width = "100%";
        progressPercent.innerText = "100%";
        progressStage.innerText = "Complete! Merged file ready.";
        statSpeed.innerText = "Done";
        statEta.innerText = "0s";

        // Show completed notification
        downloadReadyNotice.classList.remove("hidden");
        manualDownloadLink.href = task.download_url;

        // Auto-trigger browser download delivery
        triggerBrowserDownload(task.download_url);

        startDownloadBtn.disabled = false;
        startDownloadBtn.classList.remove("opacity-50", "cursor-not-allowed");
      } else if (task.status === "error") {
        clearInterval(activePollInterval);
        startDownloadBtn.disabled = false;
        startDownloadBtn.classList.remove("opacity-50", "cursor-not-allowed");
        progressCard.classList.add("hidden");
        showError(task.error || "An error occurred during video download and merge.");
      }

    } catch (err) {
      clearInterval(activePollInterval);
      startDownloadBtn.disabled = false;
      startDownloadBtn.classList.remove("opacity-50", "cursor-not-allowed");
      showError(err.message);
    }
  }, 1000);
}

// Auto-trigger delivery to browser
function triggerBrowserDownload(url) {
  const hiddenLink = document.createElement("a");
  hiddenLink.href = url;
  hiddenLink.setAttribute("download", "");
  document.body.appendChild(hiddenLink);
  hiddenLink.click();
  document.body.removeChild(hiddenLink);
}

