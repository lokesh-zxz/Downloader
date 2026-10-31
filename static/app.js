// Initialize Lucide icons
document.addEventListener("DOMContentLoaded", () => {
  if (window.lucide) lucide.createIcons();
  checkFFmpegStatus();
});

// App State
let currentVideoData = null;
let selectedResolution = null;
let activePollInterval = null;

// Sonner-style Toast Notification System (Emil Kowalski philosophy)
const sonnerContainer = document.getElementById("sonnerContainer");

function showToast(message, type = "info", duration = 4000) {
  if (!sonnerContainer) return;

  const toast = document.createElement("div");
  toast.className = "sonner-toast";

  let iconHtml = '<i data-lucide="info" class="w-4 h-4 text-blue-400 flex-shrink-0"></i>';
  if (type === "error") {
    iconHtml = '<i data-lucide="alert-circle" class="w-4 h-4 text-rose-400 flex-shrink-0"></i>';
  } else if (type === "success") {
    iconHtml = '<i data-lucide="check-circle" class="w-4 h-4 text-emerald-400 flex-shrink-0"></i>';
  }

  toast.innerHTML = `
    ${iconHtml}
    <div class="flex-1 text-xs leading-relaxed">${message}</div>
    <button class="tactile-btn text-slate-400 hover:text-white p-1">
      <i data-lucide="x" class="w-3.5 h-3.5"></i>
    </button>
  `;

  const closeBtn = toast.querySelector("button");
  const dismiss = () => {
    toast.classList.remove("visible");
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 250);
  };

  closeBtn.onclick = dismiss;

  sonnerContainer.appendChild(toast);
  if (window.lucide) lucide.createIcons();

  // Animate in via class
  requestAnimationFrame(() => {
    toast.classList.add("visible");
  });

  if (duration > 0) {
    setTimeout(dismiss, duration);
  }
}

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
const progressTitle = document.getElementById("progressTitle");
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

// Check FFmpeg status
async function checkFFmpegStatus() {
  try {
    const res = await fetch("/api/system-status");
    const data = await res.json();
    if (data.installed) {
      ffmpegStatusBtn.className = "tactile-btn flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-emerald-500/25 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/15";
      ffmpegStatusBtn.innerHTML = `
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
        <span class="tnum text-[11px]">FFmpeg Ready</span>
      `;
    } else {
      ffmpegStatusBtn.className = "tactile-btn flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-amber-500/25 bg-amber-500/10 text-amber-300 hover:bg-amber-500/15 cursor-pointer";
      ffmpegStatusBtn.innerHTML = `
        <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
        <span class="tnum text-[11px]">Install FFmpeg</span>
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
      copyText.innerText = "Copied";
      showToast("Command copied to clipboard", "success", 2500);
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

// Quick Sample links
document.querySelectorAll(".sample-link").forEach(btn => {
  btn.onclick = () => {
    videoUrlInput.value = btn.dataset.url;
    triggerFetch();
  };
});

// Form Submission
fetchForm.onsubmit = (e) => {
  e.preventDefault();
  triggerFetch();
};

async function triggerFetch() {
  const url = videoUrlInput.value.trim();
  if (!url) return;

  resultCard.classList.add("hidden");
  progressCard.classList.add("hidden");
  currentVideoData = null;
  selectedResolution = null; // Clear previous selection
  if (activePollInterval) clearInterval(activePollInterval);

  // Set loading state
  fetchBtn.disabled = true;
  fetchBtnText.innerText = "Inspecting...";
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
      throw new Error(data.detail || "Failed to inspect video stream.");
    }

    currentVideoData = data;
    renderVideoMetadata(data);
    showToast(`Loaded "${data.title.slice(0, 40)}..."`, "success", 3000);
  } catch (err) {
    showToast(err.message || "Failed to connect to backend server.", "error", 6000);
  } finally {
    fetchBtn.disabled = false;
    fetchBtnText.innerText = "Inspect";
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

  const resolutions = data.resolutions || [];

  // Default selection: pick 2160p if available, else 1080p, else first available
  if (!selectedResolution) {
    selectedResolution = resolutions.find(r => r.height === 2160 && r.is_available)
      || resolutions.find(r => r.height === 1080 && r.is_available)
      || resolutions.find(r => r.is_available)
      || resolutions[0];
  }

  // Populate Resolutions Grid
  resolutionGrid.innerHTML = "";

  resolutions.forEach((res, idx) => {
    const isSelected = selectedResolution && (
      (res.type === "audio" && selectedResolution.type === "audio") ||
      (res.type === "video" && selectedResolution.type === "video" && selectedResolution.height === res.height)
    );

    const card = document.createElement("div");
    card.setAttribute("data-res-idx", idx);
    card.className = `format-card p-2.5 rounded-xl cursor-pointer flex items-center justify-between select-none ${
      isSelected ? "selected" : ""
    } ${!res.is_available ? "opacity-35 pointer-events-none" : ""}`;

    let tagClass = "bg-white/[0.05] text-slate-300 border-white/[0.08]";
    if (res.is_4k) tagClass = "bg-blue-500/20 text-blue-300 border-blue-500/30";
    else if (res.height === 1440) tagClass = "bg-purple-500/15 text-purple-300 border-purple-500/20";
    else if (res.height === 1080) tagClass = "bg-emerald-500/15 text-emerald-300 border-emerald-500/20";

    card.innerHTML = `
      <div class="flex items-center space-x-2.5 pointer-events-none">
        <div class="radio-indicator w-3.5 h-3.5 rounded-full border flex items-center justify-center transition-all ${
          isSelected ? 'border-brand-blue bg-brand-blue' : 'border-white/20 bg-transparent'
        }">
          ${isSelected ? '<div class="w-1.5 h-1.5 rounded-full bg-white"></div>' : ''}
        </div>
        <div>
          <div class="flex items-center space-x-1.5">
            <span class="text-xs font-semibold text-white tracking-tight">${res.name}</span>
            <span class="text-[9px] px-1 py-0.2 rounded font-medium border ${tagClass}">${res.badge}</span>
          </div>
          <span class="text-[10px] text-slate-400 tnum">${res.fps} &bull; ${res.estimated_size}</span>
        </div>
      </div>
      <div class="pointer-events-none">
        ${res.is_4k ? '<span class="text-[9px] font-semibold text-blue-400 uppercase tracking-wider">4K UHD</span>' : ''}
      </div>
    `;

    // Interactive Selection Handler: Updates selectedResolution and DOM state immediately
    card.addEventListener("click", () => {
      selectedResolution = res;

      // Update all cards visually without rerendering
      const allCards = resolutionGrid.querySelectorAll(".format-card");
      allCards.forEach((c, cIdx) => {
        const item = resolutions[cIdx];
        const match = item && (
          (item.type === "audio" && res.type === "audio") ||
          (item.type === "video" && res.type === "video" && item.height === res.height)
        );

        const radio = c.querySelector(".radio-indicator");
        if (match) {
          c.classList.add("selected");
          if (radio) {
            radio.className = "radio-indicator w-3.5 h-3.5 rounded-full border border-brand-blue bg-brand-blue flex items-center justify-center transition-all";
            radio.innerHTML = '<div class="w-1.5 h-1.5 rounded-full bg-white"></div>';
          }
        } else {
          c.classList.remove("selected");
          if (radio) {
            radio.className = "radio-indicator w-3.5 h-3.5 rounded-full border border-white/20 bg-transparent flex items-center justify-center transition-all";
            radio.innerHTML = '';
          }
        }
      });

      updateDownloadBtnText();
    });

    resolutionGrid.appendChild(card);
  });

  updateDownloadBtnText();
  resultCard.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();
}

function updateDownloadBtnText() {
  if (!selectedResolution) return;
  if (selectedResolution.type === "audio") {
    startDownloadBtnText.innerText = "Download MP3 Audio (Lossless)";
  } else if (selectedResolution.is_4k) {
    startDownloadBtnText.innerText = "Download 4K Ultra HD (2160p) with Merged Audio";
  } else {
    startDownloadBtnText.innerText = `Download ${selectedResolution.badge || selectedResolution.name} MP4`;
  }
}

// Start Download
startDownloadBtn.onclick = async () => {
  if (!currentVideoData || !selectedResolution) return;

  progressCard.classList.remove("hidden");
  downloadReadyNotice.classList.add("hidden");
  progressBar.style.width = "4%";
  progressPercent.innerText = "0%";
  
  const qualityLabel = selectedResolution.badge || selectedResolution.name || "Video";
  if (progressTitle) {
    progressTitle.innerText = `Processing ${qualityLabel}`;
  }
  progressStage.innerText = "Initializing worker...";
  statSpeed.innerText = "--";
  statEta.innerText = "--";

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
    showToast(`Download started for ${qualityLabel}`, "info", 3000);
    pollTaskStatus(taskId);

  } catch (err) {
    showToast(err.message || "Failed to start download.", "error", 6000);
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
        progressBar.style.width = `${Math.max(4, task.percent || 8)}%`;
        progressPercent.innerText = `${task.percent || 0}%`;
        progressStage.innerText = task.stage || "Downloading stream tracks...";
        statSpeed.innerText = task.speed || "Calculating...";
        statEta.innerText = task.eta || "Calculating...";
      } else if (task.status === "processing") {
        progressBar.style.width = "99%";
        progressPercent.innerText = "99%";
        progressStage.innerText = task.stage || "Merging video & audio with FFmpeg...";
        statSpeed.innerText = "Merging";
        statEta.innerText = "Finalizing";
      } else if (task.status === "completed") {
        clearInterval(activePollInterval);
        progressBar.style.width = "100%";
        progressPercent.innerText = "100%";
        progressStage.innerText = "Finished. Ready for playback.";
        statSpeed.innerText = "Complete";
        statEta.innerText = "0s";

        downloadReadyNotice.classList.remove("hidden");
        manualDownloadLink.href = task.download_url;

        triggerBrowserDownload(task.download_url);
        showToast("Download finished! File sent to your browser.", "success", 5000);

        startDownloadBtn.disabled = false;
        startDownloadBtn.classList.remove("opacity-50", "cursor-not-allowed");
      } else if (task.status === "error") {
        clearInterval(activePollInterval);
        startDownloadBtn.disabled = false;
        startDownloadBtn.classList.remove("opacity-50", "cursor-not-allowed");
        progressCard.classList.add("hidden");
        showToast(task.error || "An error occurred during video download and merge.", "error", 7000);
      }

    } catch (err) {
      clearInterval(activePollInterval);
      startDownloadBtn.disabled = false;
      startDownloadBtn.classList.remove("opacity-50", "cursor-not-allowed");
      showToast(err.message, "error", 6000);
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
