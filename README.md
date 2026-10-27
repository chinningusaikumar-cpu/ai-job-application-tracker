# AI Job Application Tracker

React + FastAPI job tracker with worldwide remote job discovery, optional local job listings, resume-text matching, member accounts, and private saved searches.

## Global search feature

- Keyword/title and skill search
- Country and city/region filters
- Experience, workplace, and employment type filters
- Himalayas public remote-jobs API (no API key required)
- Optional Adzuna country/city listings (credentials required)
- Pagination and de-duplication
- Original apply links and source attribution
- Resume keyword-overlap match score
- Member login and per-member saved searches

Coverage depends on each provider; no single API contains every job worldwide. This MVP discovers and links to jobs; it does not submit applications automatically.

## Run on Windows

Prerequisites: Python 3.10+, Node.js 18+, Git. SQLite is used by default for local testing.

### Backend (PowerShell terminal 1)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat`.

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/api/health

### Frontend (PowerShell terminal 2)

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally http://localhost:5173.

### Optional Adzuna listings

Register for credentials at https://developer.adzuna.com/. Add your app ID and key to `backend/.env` as `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`, then restart Uvicorn. Without these credentials, the public remote job source still works, but local-city coverage is limited.

### API test

Register through `POST /api/members/register` in Swagger at http://127.0.0.1:8000/docs, then authorize using the returned bearer token. Test `POST /api/global-jobs/search` with:

```json
{
  "keyword": "Software Developer",
  "country": "Worldwide",
  "locations": ["Hyderabad", "Bangalore", "Chennai"],
  "experience": "Entry level / Fresher",
  "workplace": "Any",
  "employment_type": "Any",
  "page": 1,
  "page_size": 20,
  "resume_text": "Python SQL React CSE graduate problem solving"
}
```

Also test `POST /api/saved-searches` and `GET /api/saved-searches`. Register a second test account to verify that saved searches remain private to each member.

## Before deployment

Set a strong `JWT_SECRET`, configure PostgreSQL through `DATABASE_URL`, enable HTTPS, restrict CORS to your real website, add email verification/password reset, rate-limit authentication, and use database migrations. Keep `.env` secrets out of GitHub. Resume text is used for match scoring; avoid saving sensitive personal information in saved searches. Follow each job source's API terms, attribution rules, and expiration policies.
