@echo off
setlocal
cd /d "%~dp0site"
echo ========================================================
echo  Grads4Grads - Professor Demonstration
 echo  Study resources, Q^&A, practice, Grand Quiz and PDF viewer
 echo ========================================================
where py >nul 2>nul
if %errorlevel% equ 0 (
  start "" "http://127.0.0.1:8000/index.html"
  py -3 -m http.server 8000 --bind 127.0.0.1
) else (
  where python >nul 2>nul
  if %errorlevel% equ 0 (
    start "" "http://127.0.0.1:8000/index.html"
    python -m http.server 8000 --bind 127.0.0.1
  ) else (
    echo Python is not installed. Install Python 3 from python.org and rerun this file.
    pause
  )
)
endlocal
