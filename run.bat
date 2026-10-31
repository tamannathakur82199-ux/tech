@echo off
echo Starting Campus Complaints and Suggestions Platform...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m uvicorn campus_complaints.main:app --host 127.0.0.1 --port 8000 --reload
) else if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m uvicorn campus_complaints.main:app --host 127.0.0.1 --port 8000 --reload
) else (
    python -m uvicorn campus_complaints.main:app --host 127.0.0.1 --port 8000 --reload
)
pause
