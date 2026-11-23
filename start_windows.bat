@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment...
  py -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist ".env" (
  copy .env.example .env >nul
  echo Created .env. Add your Gemini API key before using the AI Assistant.
)
python app.py
pause
