@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python not found. Install from https://www.python.org/downloads/ and check "Add to PATH".
    pause
    exit /b 1
)

python -c "import PIL" 2>nul
if errorlevel 1 (
    echo Installing Pillow...
    python -m pip install --quiet Pillow
)

python -c "import tkinterdnd2" 2>nul
if errorlevel 1 (
    echo Installing tkinterdnd2 (drag and drop support)...
    python -m pip install --quiet tkinterdnd2
)

python app.py
