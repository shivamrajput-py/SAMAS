@echo off
echo Starting SAMAS Backend API...
start cmd /k "cd backend && .\venv\Scripts\python -m uvicorn app.api:app --host 0.0.0.0 --port 8000"

echo Starting SAMAS Next.js Frontend...
start cmd /k "cd frontend && npm run dev"

echo Both services are starting!
echo Next.js frontend will be available at: http://localhost:3000
echo FastAPI backend will be available at: http://localhost:8000
