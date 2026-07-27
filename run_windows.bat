@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First install is required.
  echo py -m venv .venv
  echo .venv\Scripts\activate
  echo pip install -r requirements.txt
  pause
  exit /b
)
call .venv\Scripts\activate
streamlit run app.py
