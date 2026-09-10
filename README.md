# AI Job Application Tracker

An intelligent job application tracker that analyzes resumes against job descriptions, calculates a match score, identifies skill gaps, and tracks applications.

## Tech Stack
- Frontend: React + Vite + Tailwind CSS
- Backend: FastAPI
- Database: PostgreSQL
- AI/NLP: Python (spaCy/scikit-learn; optional LLM integration)
- Authentication: JWT

## Project Structure
- `frontend/` — React application
- `backend/` — FastAPI REST API
- `ml/` — resume parsing, skill extraction, and job matching

## Development
Backend:
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```
