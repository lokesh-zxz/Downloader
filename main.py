import os
import urllib.parse
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from ffmpeg_utils import get_ffmpeg_status
from downloader import (
    fetch_video_metadata,
    start_download_task,
    get_task_status,
    cleanup_task_files,
    DOWNLOADS_DIR,
)

app = FastAPI(
    title="4K Video Downloader API",
    description="FastAPI + yt-dlp backend with FFmpeg 4K stream merging and automatic browser delivery",
    version="1.0.0"
)

# CORS middleware for local development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static folder exists
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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
    return {"message": "4K Video Downloader API is running. UI index.html not yet initialized."}

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
    
    # Quick basic validation
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

    # Validate height
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

    # Background task to clean up task directory after response is sent (after 5 minutes or schedule)
    # Keeping it accessible for download, or schedule cleanup
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{urllib.parse.quote(filename)}"'}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
