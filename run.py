import sys
import os
import uvicorn
from ffmpeg_utils import get_ffmpeg_status

def main():
    print("=" * 60)
    print("  ULTRA 4K VIDEO DOWNLOADER - FASTAPI + YT-DLP")
    print("=" * 60)

    # Check FFmpeg status
    status = get_ffmpeg_status()
    if status["installed"]:
        print(f"[+] FFmpeg Detected: {status['version']}")
        print(f"[+] Path: {status['ffmpeg_dir']}")
    else:
        print("[!] NOTICE: FFmpeg is not found in standard system paths.")
        print("[!] Note: YouTube 4K (2160p) separates video & audio streams.")
        print("[!] To enable 4K merging on Windows, run this in PowerShell:")
        print(f"      {status['instructions']['windows']}")
        print("    (The web UI also includes a 1-click guide and copy button)")
    
    print("-" * 60)
    print("[*] Starting web server on: http://127.0.0.1:8000")
    print("[*] Press Ctrl+C to stop the server.")
    print("=" * 60)

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()

