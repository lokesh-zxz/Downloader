@echo off
title 4K Video Downloader Server
echo ========================================================
echo   Launching 4K Video Downloader (FastAPI + yt-dlp)
echo ========================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python run.py
) else (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" run.py
)

pause

