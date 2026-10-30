# 🚀 4K Ultra HD Video Downloader (FastAPI + yt-dlp + FFmpeg)

A modern, responsive full-stack web application that allows users to download videos in up to **4K resolution (2160p @ 60fps)** by pasting a video link.

---

## 🌟 Features

- **True 4K (2160p), 1440p (2K), & 1080p (Full HD) Support**: Pulls separate high-bitrate video streams and high-fidelity audio streams.
- **Automated FFmpeg Stream Merging**: Merges DASH video and audio streams seamlessly into a single `.mp4` container.
- **Audio Extraction**: High-quality 320kbps MP3 audio download option.
- **FastAPI & Async Background Workers**: Non-blocking download tasks with real-time speed, ETA, and progress tracking.
- **Modern Responsive UI**: Built with Tailwind CSS, Lucide icons, glassmorphism, responsive cards, and dynamic spinners.
- **Direct Browser Delivery**: Automatically delivers the final `.mp4` file directly to the browser upon completion.
- **Built-in System Diagnostics**: Dynamically detects FFmpeg availability and provides 1-click installation guidance.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.14, FastAPI, Uvicorn, yt-dlp, python-multipart
- **Frontend**: HTML5, Tailwind CSS, Lucide Icons, Vanilla ES6 JavaScript
- **Media Engine**: FFmpeg (used by yt-dlp to stitch video + audio tracks)

---

## ⚡ Quick Start

### 1. Ensure Dependencies Are Installed
```powershell
pip install -r requirements.txt
```

### 2. Start the Application
Run via the provided launcher:
```powershell
python run.py
```
Or directly using Uvicorn:
```powershell
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Then open your browser to **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

---

## 🎬 Crucial: FFmpeg Setup for 4K Video Merging (Windows)

> [!IMPORTANT]
> Video platforms like YouTube separate high-resolution video (1080p, 1440p, 2160p 4K) from audio tracks into separate streams. **FFmpeg** is required on your machine for `yt-dlp` to merge these two tracks into a standard playable `.mp4` file.

### Option A: 1-Click Install via Windows Package Manager (Recommended)
Open **PowerShell** or **Command Prompt** as Administrator (or standard user) and run:
```powershell
winget install Gyan.FFmpeg
```

### Option B: Using Chocolatey (if installed)
```powershell
choco install ffmpeg
```

### Option C: Using Scoop (if installed)
```powershell
scoop install ffmpeg
```

### Option D: Manual Download
1. Download the latest build from [gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/) (`ffmpeg-git-full.7z` or `ffmpeg-release-essentials.zip`).
2. Extract to `C:\ffmpeg`.
3. Add `C:\ffmpeg\bin` to your system Environment Variables `PATH`.

Once installed, restart your terminal or the web server. The app automatically detects FFmpeg and displays **"FFmpeg Ready (4K Merging Active)"** in the top navbar.

