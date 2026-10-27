from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.global_jobs import router as global_jobs_router

app = FastAPI(title="AI Job Application Tracker API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(global_jobs_router)

@app.get("/")
def root():
    return {"message": "AI Job Application Tracker API is running"}

@app.get("/api/health")
def health():
    return {"status": "healthy"}
