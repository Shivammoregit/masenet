@echo off
echo ===================================
echo Plant Disease Detector - VLM Server
echo ===================================
echo.

cd /d "%~dp0"

echo Ensure dependencies are installed:
echo   pip install -r requirements.txt
echo.
echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

python -m uvicorn server:app --reload --port 8000
