from __future__ import annotations
import os
import re
import math
import uuid
import time
import logging
import threading
import tempfile
from typing import Dict, Any, List, Optional
import yt_dlp
from ffmpeg_utils import find_ffmpeg

# Optional browser TLS impersonation (bypasses Cloudflare & strict ISP/TLS restrictions)
try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
    CHROME_TARGET = ImpersonateTarget.from_str("chrome")
except Exception:
    CHROME_TARGET = None

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

logger = logging.getLogger("yt_downloader")
logger.setLevel(logging.INFO)

# Determine safe downloads directory (writable on local Windows and serverless /tmp)
def get_downloads_dir() -> str:
    # First attempt local downloads directory (for local dev)
    try:
        local_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "downloads"))
        os.makedirs(local_dir, exist_ok=True)
        # Test write permission
        test_file = os.path.join(local_dir, ".perm_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return local_dir
    except (OSError, PermissionError):
        # Fallback to system /tmp directory (essential for Vercel / AWS Lambda)
        tmp_dir = os.path.join(tempfile.gettempdir(), "downloader_files")
        os.makedirs(tmp_dir, exist_ok=True)
        return tmp_dir

DOWNLOADS_DIR = get_downloads_dir()

# In-memory store for download tasks
tasks_lock = threading.Lock()
download_tasks: Dict[str, Dict[str, Any]] = {}

def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "Unknown"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def format_number(val: Optional[int]) -> str:
    if not val:
        return "0"
    if val >= 1_000_000_000:
        return f"{val / 1_000_000_000:.1f}B"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{val / 1_000:.1f}K"
    return str(val)

def format_bytes(b: Optional[float]) -> str:
    if not b or b <= 0:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024.0:
            return f"{b:.1f} {unit}"
        b /= 1024.0
    return f"{b:.1f} PB"

def clean_filename(filename: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def fetch_video_metadata(url: str) -> Dict[str, Any]:
    """
    Extract video title, thumbnail, duration, author, and available resolutions
    (including 4K/2160p, 1440p, 1080p, 720p, etc.).
    """
    ffmpeg_dir = find_ffmpeg()

    ydl_opts = {
        "skip_download": True,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "nocheckcertificate": True,
        "http_headers": DEFAULT_HEADERS,
        "socket_timeout": 20,
    }
    if CHROME_TARGET:
        ydl_opts["impersonate"] = CHROME_TARGET
    if ffmpeg_dir:
        ydl_opts["ffmpeg_location"] = ffmpeg_dir

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            err_str = str(e)
            if "UNEXPECTED_EOF" in err_str or "SSL" in err_str:
                err_str = "SSL handshake failed or connection closed by host/ISP. If this site is restricted by your local network/ISP, enable a VPN to fetch."
            elif "timed out" in err_str.lower():
                err_str = "Connection to video host timed out. The provider might be blocked or unreachable from your current IP."
            raise ValueError(f"Failed to fetch video: {err_str}")

    if not info:
        raise ValueError("Could not extract video metadata.")

    # Target resolution tiers
    target_tiers = [
        {"height": 2160, "name": "4K Ultra HD", "badge": "2160p (4K)", "is_4k": True},
        {"height": 1440, "name": "2K Quad HD", "badge": "1440p (2K)", "is_4k": False},
        {"height": 1080, "name": "Full HD", "badge": "1080p (FHD)", "is_4k": False},
        {"height": 720, "name": "High Definition", "badge": "720p (HD)", "is_4k": False},
        {"height": 480, "name": "Standard Definition", "badge": "480p (SD)", "is_4k": False},
        {"height": 360, "name": "Basic Quality", "badge": "360p (SD)", "is_4k": False},
    ]

    formats = info.get("formats", [])
    duration = info.get("duration", 0)

    # Check best available audio format size/bitrate
    best_audio_size = 0
    best_audio_abr = 128
    for f in formats:
        if f.get("vcodec") == "none" and f.get("acodec") != "none":
            abr = f.get("abr") or 0
            if abr > best_audio_abr:
                best_audio_abr = abr
            sz = f.get("filesize") or f.get("filesize_approx")
            if sz and sz > best_audio_size:
                best_audio_size = sz

    if not best_audio_size and duration > 0:
        best_audio_size = (best_audio_abr * 1000 / 8) * duration

    # Map available video heights from actual formats
    available_heights = {}
    for f in formats:
        h = f.get("height")
        if not h or f.get("vcodec") == "none":
            continue

        fps = f.get("fps") or 30
        filesize = f.get("filesize") or f.get("filesize_approx")
        vbr = f.get("vbr") or 0

        if h not in available_heights:
            available_heights[h] = {
                "height": h,
                "fps": fps,
                "format_id": f.get("format_id"),
                "ext": f.get("ext", "mp4"),
                "filesize": filesize,
                "vbr": vbr,
                "vcodec": f.get("vcodec", "video"),
            }
        else:
            if fps > available_heights[h]["fps"]:
                available_heights[h]["fps"] = fps
            if filesize and (not available_heights[h]["filesize"] or filesize > available_heights[h]["filesize"]):
                available_heights[h]["filesize"] = filesize
            if vbr and vbr > available_heights[h]["vbr"]:
                available_heights[h]["vbr"] = vbr

    max_height = max(available_heights.keys()) if available_heights else 1080

    resolutions = []
    for tier in target_tiers:
        target_h = tier["height"]
        is_available = any(h >= target_h for h in available_heights.keys()) if available_heights else True
        best_match = available_heights.get(target_h)
        if not best_match:
            candidates = [h for h in available_heights.keys() if h <= target_h]
            if candidates:
                best_match = available_heights[max(candidates)]

        fps_val = best_match["fps"] if best_match else 60 if target_h >= 1080 else 30
        fps_label = f"{fps_val}fps" if fps_val else "30fps"

        estimated_size = None
        if best_match and best_match.get("filesize"):
            estimated_size = best_match["filesize"] + best_audio_size
        elif best_match and best_match.get("vbr") and duration > 0:
            estimated_size = ((best_match["vbr"] + best_audio_abr) * 1000 / 8) * duration
        elif duration > 0:
            bitrate_map = {2160: 25000, 1440: 12000, 1080: 5000, 720: 2500, 480: 1200, 360: 700}
            est_br = bitrate_map.get(target_h, 3000)
            estimated_size = (est_br * 1000 / 8) * duration

        size_label = format_bytes(estimated_size) if estimated_size else "Varies"

        resolutions.append({
            "height": target_h,
            "name": tier["name"],
            "badge": tier["badge"],
            "fps": fps_label,
            "estimated_size": size_label,
            "is_available": is_available,
            "is_4k": tier["is_4k"],
            "type": "video",
            "format_string": f"bestvideo[height<={target_h}]+bestaudio/best[height<={target_h}]/best",
        })

    audio_est_size = format_bytes(best_audio_size) if best_audio_size else "3 - 10 MB"
    resolutions.append({
        "height": 0,
        "name": "Audio Only (MP3)",
        "badge": "Audio (MP3 / 320kbps)",
        "fps": "Audio only",
        "estimated_size": audio_est_size,
        "is_available": True,
        "is_4k": False,
        "type": "audio",
        "format_string": "bestaudio/best",
    })

    thumbnails = info.get("thumbnails", [])
    thumbnail_url = info.get("thumbnail")
    if thumbnails:
        sorted_thumbs = sorted(
            [t for t in thumbnails if t.get("url")],
            key=lambda t: (t.get("width") or 0) * (t.get("height") or 0),
            reverse=True
        )
        if sorted_thumbs:
            thumbnail_url = sorted_thumbs[0]["url"]

    return {
        "id": info.get("id"),
        "title": info.get("title", "Untitled Video"),
        "uploader": info.get("uploader") or info.get("channel") or "Unknown Creator",
        "uploader_url": info.get("uploader_url") or info.get("channel_url"),
        "thumbnail": thumbnail_url,
        "duration": duration,
        "duration_str": format_duration(duration),
        "view_count": info.get("view_count", 0),
        "view_count_str": format_number(info.get("view_count")),
        "upload_date": info.get("upload_date"),
        "webpage_url": info.get("webpage_url", url),
        "max_height": max_height,
        "has_4k": max_height >= 2160,
        "has_1440p": max_height >= 1440,
        "resolutions": resolutions,
    }


def download_worker(task_id: str, url: str, height: int, is_audio_only: bool):
    """
    Background worker that runs yt-dlp to download and merge 4K video + audio via FFmpeg.
    """
    downloads_root = get_downloads_dir()
    task_dir = os.path.join(downloads_root, task_id)
    os.makedirs(task_dir, exist_ok=True)
    ffmpeg_dir = find_ffmpeg()

    def update_task(**kwargs):
        with tasks_lock:
            if task_id in download_tasks:
                download_tasks[task_id].update(kwargs)

    def progress_hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            percent = 0.0
            if total > 0:
                percent = round((downloaded / total) * 100, 1)

            speed_str = d.get("_speed_str") or ""
            eta_str = d.get("_eta_str") or ""
            filename = os.path.basename(d.get("filename", ""))

            stage = "Downloading video stream..."
            if "audio" in filename.lower() or d.get("info_dict", {}).get("acodec") and not d.get("info_dict", {}).get("vcodec"):
                stage = "Downloading audio stream..."

            update_task(
                status="downloading",
                stage=stage,
                percent=percent,
                speed=speed_str.strip(),
                eta=eta_str.strip(),
                downloaded_bytes=downloaded,
                total_bytes=total,
            )

        elif status == "finished":
            update_task(
                status="processing",
                stage="Merging 4K video & audio streams with FFmpeg...",
                percent=99.0,
                speed="Merging...",
                eta="Finalizing",
            )

    try:
        update_task(status="starting", stage="Initializing yt-dlp download...", percent=5.0)

        if is_audio_only:
            format_str = "bestaudio/best"
        elif height > 0:
            format_str = (
                f"bestvideo[height={height}]+bestaudio/"
                f"best[height={height}]/"
                f"bestvideo[height<={height}]+bestaudio/"
                f"best[height<={height}]/"
                f"best"
            )
        else:
            format_str = "bestvideo+bestaudio/best"

        outtmpl = os.path.join(task_dir, "%(title).150B [%(id)s].%(ext)s")

        ydl_opts: Dict[str, Any] = {
            "format": format_str,
            "outtmpl": outtmpl,
            "progress_hooks": [progress_hook],
            "noplaylist": True,
            "quiet": False,
            "no_warnings": False,
            "retries": 10,
            "fragment_retries": 10,
        }

        if is_audio_only:
            if ffmpeg_dir:
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
        else:
            ydl_opts["merge_output_format"] = "mp4"

        if ffmpeg_dir:
            ydl_opts["ffmpeg_location"] = ffmpeg_dir

        update_task(status="downloading", stage="Connecting to video provider...", percent=10.0)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        produced_files = [
            f for f in os.listdir(task_dir)
            if not f.endswith(".part") and not f.endswith(".ytdl") and not f.endswith(".temp")
        ]

        if not produced_files:
            raise FileNotFoundError("Merged video file could not be found after processing.")

        produced_files.sort(key=lambda f: os.path.getsize(os.path.join(task_dir, f)), reverse=True)
        final_filename = produced_files[0]
        final_filepath = os.path.join(task_dir, final_filename)
        filesize = os.path.getsize(final_filepath)

        update_task(
            status="completed",
            stage="Complete! Ready for download.",
            percent=100.0,
            filename=final_filename,
            filepath=final_filepath,
            filesize=filesize,
            filesize_str=format_bytes(filesize),
            download_url=f"/api/download/file/{task_id}",
        )

    except Exception as e:
        logger.exception("Download failed:")
        error_msg = str(e)
        if "ffmpeg" in error_msg.lower():
            error_msg += " (FFmpeg is required to merge 4K video and audio tracks)."
        update_task(
            status="error",
            stage="Failed",
            error=error_msg,
        )


def start_download_task(url: str, height: int, is_audio_only: bool = False) -> str:
    task_id = str(uuid.uuid4())
    with tasks_lock:
        download_tasks[task_id] = {
            "task_id": task_id,
            "url": url,
            "height": height,
            "is_audio_only": is_audio_only,
            "status": "queued",
            "stage": "Queueing task...",
            "percent": 0.0,
            "speed": "",
            "eta": "",
            "filename": "",
            "filepath": "",
            "filesize": 0,
            "filesize_str": "",
            "error": None,
            "created_at": time.time(),
        }

    thread = threading.Thread(
        target=download_worker,
        args=(task_id, url, height, is_audio_only),
        daemon=True
    )
    thread.start()
    return task_id


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    with tasks_lock:
        return download_tasks.get(task_id)


def cleanup_task_files(task_id: str):
    downloads_root = get_downloads_dir()
    task_dir = os.path.join(downloads_root, task_id)
    if os.path.exists(task_dir):
        try:
            for item in os.listdir(task_dir):
                p = os.path.join(task_dir, item)
                if os.path.isfile(p):
                    os.remove(p)
            os.rmdir(task_dir)
        except Exception as e:
            logger.warning(f"Error cleaning up task {task_id}: {e}")
    with tasks_lock:
        download_tasks.pop(task_id, None)
