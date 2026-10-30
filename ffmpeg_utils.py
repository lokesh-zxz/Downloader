import os
import shutil
import glob
import subprocess

def find_ffmpeg() -> str | None:
    """
    Search for ffmpeg executable in PATH and standard Windows/Unix locations.
    Returns the path to the directory containing ffmpeg, or the executable path, or None.
    """
    # 1. Check if ffmpeg is in PATH
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
    winget_pattern = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin")
    matches = glob.glob(winget_pattern)
    for m in matches:
        if os.path.isfile(os.path.join(m, "ffmpeg.exe")):
            return m

    # 4. Check AppData local programs or similar
    extra_pattern = os.path.expandvars(r"%LOCALAPPDATA%\Programs\ffmpeg*\bin")
    matches = glob.glob(extra_pattern)
    for m in matches:
        if os.path.isfile(os.path.join(m, "ffmpeg.exe")):
            return m

    return None

def get_ffmpeg_status() -> dict:
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
        except Exception as e:
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

