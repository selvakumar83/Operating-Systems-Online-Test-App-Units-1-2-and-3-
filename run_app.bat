@echo off
setlocal
cd /d "%~dp0"
echo Starting Operating Systems Online Test...
py -m streamlit run app.py
if errorlevel 1 (
  echo.
  echo The app did not start. Try installing requirements with:
  echo   py -m pip install -r requirements.txt
  echo Then run this file again.
  pause
)
endlocal
