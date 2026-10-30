from __future__ import annotations
import os
import shutil
import glob
import subprocess
from typing import Optional, Dict, Any

def find_ffmpeg() -> Optional[str]:
    """
    Search for ffmpeg executable in PATH and standard Windows/Unix locations.
    Returns the path to the directory containing ffmpeg, or None.
    """
    # 1. Check if ffmpeg is in system PATH (Linux / macOS / Windows)
    which_path = shutil.which("ffmpeg")
    if which_path:
        return os.path.dirname(which_path)

    # 2. Check standard Windows locations
    win_paths = [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
        r"C:\ProgramData\chocolatey\bin",
        os.path.expandvars(r"%USERPROFILE%\scoop\shims"),
    ]

    for p in win_paths:
        if os.path.isfile(os.path.join(p, "ffmpeg.exe")):
            return p

    # 3. Check WinGet package locations
    try:
        winget_pattern = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin")
        matches = glob.glob(winget_pattern)
        for m in matches:
            if os.path.isfile(os.path.join(m, "ffmpeg.exe")):
                return m
    except Exception:
        pass

    # 4. Check Linux / container common paths
    linux_paths = ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"]
    for lp in linux_paths:
        if os.path.isfile(lp):
            return os.path.dirname(lp)

    return None

def get_ffmpeg_status() -> Dict[str, Any]:
    ffmpeg_dir = find_ffmpeg()
    installed = ffmpeg_dir is not None
    version_info = "Unknown"

    if installed:
        exe = os.path.join(ffmpeg_dir, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if not os.path.exists(exe):
            exe = shutil.which("ffmpeg") or "ffmpeg"
        try:
            res = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=5)
            first_line = res.stdout.splitlines()[0] if res.stdout else "Available"
            version_info = first_line
        except Exception:
            version_info = f"Detected at {ffmpeg_dir}"

    return {
        "installed": installed,
        "ffmpeg_dir": ffmpeg_dir,
        "version": version_info,
        "instructions": {
            "windows": "winget install Gyan.FFmpeg",
            "macos": "brew install ffmpeg",
            "linux": "sudo apt update && sudo apt install ffmpeg"
        }
    }
