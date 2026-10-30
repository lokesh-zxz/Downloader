from __future__ import annotations
import os
import urllib.parse
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ffmpeg_utils import get_ffmpeg_status
from downloader import (
    fetch_video_metadata,
    start_download_task,
    get_task_status,
    cleanup_task_files,
)

app = FastAPI(
    title="4K Video Downloader API",
    description="FastAPI + yt-dlp backend with FFmpeg 4K stream merging and automatic browser delivery",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Locate static folder safely across local, Docker, and Vercel environments
def find_static_dir() -> str:
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "static")),
        os.path.abspath(os.path.join(os.getcwd(), "static")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static")),
    ]
    for p in possible_paths:
        if os.path.exists(p) and os.path.isdir(p):
            return p
    return possible_paths[0]

STATIC_DIR = find_static_dir()

# Mount static files safely
try:
    if os.path.exists(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
except Exception:
    pass

class VideoInfoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    height: int = 2160
    is_audio: bool = False

@app.get("/")
@app.head("/")
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>4K Video Downloader API is running.</h2><p>Static index.html not found.</p>")

# Explicit fallback for static files if static mount is bypassed in serverless
@app.get("/static/{filename}")
def serve_static_fallback(filename: str):
    file_path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(file_path):
        media_type = "application/javascript" if filename.endswith(".js") else "text/css" if filename.endswith(".css") else None
        return FileResponse(file_path, media_type=media_type)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/api/system-status")
def system_status():
    """
    Check if FFmpeg is configured and return installation commands if missing.
    """
    return get_ffmpeg_status()

@app.post("/api/info")
def get_video_info(payload: VideoInfoRequest):
    """
    Extract video metadata, thumbnail, duration, author, and available resolutions.
    """
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please provide a valid video URL.")
    
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    try:
        data = fetch_video_metadata(url)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download/start")
def initiate_download(payload: DownloadRequest):
    """
    Start a background download & merge task for the specified resolution.
    """
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Missing video URL.")

    height = payload.height
    is_audio = payload.is_audio

    task_id = start_download_task(url, height=height, is_audio_only=is_audio)
    return {"task_id": task_id, "status": "queued"}

@app.get("/api/download/status/{task_id}")
def check_download_status(task_id: str):
    """
    Poll status, percentage, speed, and download URL for an active task.
    """
    task = get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or expired.")
    return task

@app.get("/api/download/file/{task_id}")
def download_file(task_id: str, background_tasks: BackgroundTasks):
    """
    Serve the completed .mp4 or .mp3 file as an attachment to the user's browser.
    """
    task = get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"File is not ready. Current status: {task.get('status')}")

    filepath = task.get("filepath")
    filename = task.get("filename") or "video.mp4"

    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Processed file was not found on server disk.")

    media_type = "audio/mpeg" if filename.endswith(".mp3") else "video/mp4"

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{urllib.parse.quote(filename)}"'}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
