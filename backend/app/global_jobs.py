"""Global job discovery, member auth, resume matching, and saved searches.

Set JWT_SECRET and DATABASE_URL in production. The default SQLite database is for local development.
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

router = APIRouter(tags=["global-jobs"])
JWT_SECRET = os.getenv("JWT_SECRET", "LOCAL-ONLY-change-this-secret-before-deploying")
JWT_ALGORITHM = "HS256"
TOKEN_MINUTES = 60 * 24 * 7
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./global_job_search.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Member(Base):
    __tablename__ = "global_job_members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class SavedSearch(Base):
    __tablename__ = "global_saved_searches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("global_job_members.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    filters_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)
security = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 310_000).hex()
    return f"{salt}" + "$" + digest


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
        return hmac.compare_digest(hash_password(password, salt).split("$", 1)[1], digest)
    except (ValueError, TypeError):
        return False


def make_token(member: Member) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(member.id), "email": member.email, "iat": now, "exp": now + timedelta(minutes=TOKEN_MINUTES)}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_member(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db=Depends(get_db)) -> Member:
    if not credentials:
        raise HTTPException(status_code=401, detail="Sign in to use member-specific features.")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        member_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=401, detail="Member account not found.")
    return member


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class SearchRequest(BaseModel):
    keyword: str = Field(default="Software Developer", min_length=1, max_length=120)
    country: str = "Worldwide"
    locations: list[str] = Field(default_factory=lambda: ["Hyderabad", "Bangalore", "Chennai"])
    experience: str = "Entry level / Fresher"
    workplace: str = "Any"
    employment_type: str = "Any"
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=20, ge=5, le=50)
    resume_text: str = Field(default="", max_length=20000)


class SaveSearchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    filters: SearchRequest


def _salary(low, high, currency=""):
    if low is None and high is None:
        return "Not disclosed"
    if low is not None and high is not None:
        return f"{currency} {low:,}–{high:,}".strip()
    return f"{currency} {low if low is not None else high:,}".strip()


def _normalise_himalayas(item: dict) -> dict:
    return {
        "id": str(item.get("guid") or item.get("applicationLink") or ""),
        "title": item.get("title") or "Untitled role",
        "company": item.get("companyName") or "Company not listed",
        "location": ", ".join(item.get("locationRestrictions") or []) or "Remote / worldwide",
        "employment_type": item.get("employmentType") or "Not specified",
        "seniority": item.get("seniority") or "Not specified",
        "salary": _salary(item.get("minSalary"), item.get("maxSalary"), item.get("currency") or ""),
        "summary": item.get("excerpt") or "",
        "description": item.get("description") or "",
        "apply_url": item.get("applicationLink") or "",
        "source": "Himalayas",
        "source_url": "https://himalayas.app",
        "published_at": item.get("pubDate"),
        "match_score": 0,
    }


def _normalise_adzuna(item: dict, country_code: str) -> dict:
    loc = item.get("location") or {}
    return {
        "id": str(item.get("id") or item.get("redirect_url") or ""),
        "title": item.get("title") or "Untitled role",
        "company": (item.get("company") or {}).get("display_name") or "Company not listed",
        "location": ", ".join(loc.get("area") or []) or country_code.upper(),
        "employment_type": item.get("contract_type") or "Not specified",
        "seniority": "Not specified",
        "salary": _salary(item.get("salary_min"), item.get("salary_max")),
        "summary": item.get("description") or "",
        "description": item.get("description") or "",
        "apply_url": item.get("redirect_url") or "",
        "source": "Adzuna",
        "source_url": "https://www.adzuna.com",
        "published_at": item.get("created"),
        "match_score": 0,
    }


def _match_score(job: dict, resume_text: str) -> int:
    if not resume_text.strip():
        return 0
    haystack = " ".join(str(job.get(k) or "") for k in ("title", "description", "summary", "company", "location")).lower()
    stop = {"with", "and", "the", "for", "you", "your", "from", "that", "this", "are", "have", "will", "work", "job"}
    words = {w.strip(".,:;()[]{}!?/\\-") for w in resume_text.lower().split()}
    words = {w for w in words if len(w) >= 3 and w not in stop}
    if not words:
        return 0
    return min(100, round(100 * sum(1 for word in words if word in haystack) / len(words)))


def _experience_ok(job: dict, selected: str) -> bool:
    if selected in ("Any", "Any experience", ""):
        return True
    text = f"{job.get('title','')} {job.get('seniority','')} {job.get('summary','')}".lower()
    senior = ("senior", "lead", "principal", "manager", "director", "staff engineer")
    if selected == "Entry level / Fresher":
        junior = ("entry", "junior", "graduate", "fresher", "intern", "trainee", "new grad", "associate")
        return any(term in text for term in junior) or not any(term in text for term in senior)
    if selected == "Junior (1–3 years)":
        return any(term in text for term in ("junior", "associate", "1-3 years", "1–3 years"))
    if selected == "Mid level (3–5 years)":
        return any(term in text for term in ("mid-level", "mid level", "3-5 years", "3–5 years"))
    if selected == "Senior (5+ years)":
        return any(term in text for term in senior)
    if selected == "Internship":
        return "intern" in text or "internship" in text
    return True


@router.post("/api/members/register")
def register(payload: RegisterRequest, db=Depends(get_db)):
    email = payload.email.lower().strip()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if db.query(Member).filter(Member.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    member = Member(email=email, password_hash=hash_password(payload.password))
    db.add(member)
    db.commit()
    db.refresh(member)
    return {"access_token": make_token(member), "token_type": "bearer", "member": {"id": member.id, "email": member.email}}


@router.post("/api/members/login")
def login(payload: LoginRequest, db=Depends(get_db)):
    member = db.query(Member).filter(Member.email == payload.email.lower().strip()).first()
    if not member or not verify_password(payload.password, member.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return {"access_token": make_token(member), "token_type": "bearer", "member": {"id": member.id, "email": member.email}}


@router.get("/api/members/me")
def me(member: Member = Depends(current_member)):
    return {"id": member.id, "email": member.email}


@router.post("/api/global-jobs/search")
async def search_jobs(payload: SearchRequest, member: Member = Depends(current_member)):
    jobs, warnings = [], []
    headers = {"User-Agent": "AIJobApplicationTracker/1.0"}
    seniority = {"Entry level / Fresher": "Entry-level", "Junior (1–3 years)": "Mid-level", "Mid level (3–5 years)": "Mid-level", "Senior (5+ years)": "Senior", "Internship": "Entry-level"}
    params = {"q": payload.keyword, "page": payload.page, "sort": "recent"}
    if payload.country != "Worldwide":
        params["country"] = payload.country
    if payload.experience in seniority:
        params["seniority"] = seniority[payload.experience]
    if payload.employment_type != "Any":
        params["employment_type"] = {"Full-time": "Full Time", "Part-time": "Part Time", "Contract": "Contractor", "Internship": "Intern"}.get(payload.employment_type, payload.employment_type)
    if payload.workplace == "Remote":
        params["worldwide"] = "true"
    try:
        async with httpx.AsyncClient(timeout=12, headers=headers, follow_redirects=True) as client:
            response = await client.get("https://himalayas.app/jobs/api/search", params=params)
            response.raise_for_status()
            jobs.extend(_normalise_himalayas(x) for x in response.json().get("jobs", []))
    except (httpx.HTTPError, ValueError):
        warnings.append("Himalayas feed is temporarily unavailable.")

    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if app_id and app_key:
        locations = [x.strip() for x in payload.locations if x.strip()]
        country = payload.country.lower()
        codes = ["in"] if locations or country == "india" else (["us", "gb", "ca", "au", "de", "in"] if country == "worldwide" else [])
        import asyncio
        async with httpx.AsyncClient(timeout=12, headers=headers, follow_redirects=True) as client:
            reqs = []
            for code in codes:
                targets = locations if code == "in" and locations else [""]
                for target in targets[:3]:
                    q = {"app_id": app_id, "app_key": app_key, "results_per_page": 10, "what": payload.keyword, "content-type": "application/json"}
                    if target:
                        q["where"] = target
                    reqs.append((code, client.get(f"https://api.adzuna.com/v1/api/jobs/{code}/search/{payload.page}", params=q)))
            results = await asyncio.gather(*(r for _, r in reqs), return_exceptions=True)
            for (code, _), result in zip(reqs, results):
                if not isinstance(result, Exception) and result.is_success:
                    jobs.extend(_normalise_adzuna(x, code) for x in result.json().get("results", []))

    locations = [x.strip().lower() for x in payload.locations if x.strip()]
    filtered, seen = [], set()
    for job in jobs:
        place = str(job.get("location") or "").lower()
        searchable = f"{job.get('title','')} {job.get('summary','')} {place}".lower()
        if locations and payload.workplace != "Remote" and not any(x in place or x in searchable for x in locations):
            if not (payload.country == "Worldwide" and ("worldwide" in place or place == "remote / worldwide")):
                continue
        if payload.workplace == "On-site" and any(x in searchable for x in ("remote", "work from anywhere")):
            continue
        if payload.workplace == "Remote" and not any(x in searchable for x in ("remote", "worldwide", "anywhere")):
            continue
        if payload.employment_type != "Any":
            wanted = payload.employment_type.lower().replace("-", " ")
            actual = str(job.get("employment_type") or "").lower().replace("-", " ")
            if wanted not in actual:
                continue
        if not _experience_ok(job, payload.experience):
            continue
        key = (job.get("apply_url") or "").strip().lower() or "|".join((job.get("title", "").lower(), job.get("company", "").lower(), place))
        if key in seen:
            continue
        seen.add(key)
        job["match_score"] = _match_score(job, payload.resume_text)
        filtered.append(job)
    if payload.resume_text.strip():
        filtered.sort(key=lambda x: x["match_score"], reverse=True)
    # Each upstream source already receives the requested page number. Do not slice a second time.
    result_jobs = filtered[:payload.page_size]
    return {"jobs": result_jobs, "page": payload.page, "page_size": payload.page_size, "has_more": len(jobs) >= payload.page_size, "count": len(result_jobs), "sources": sorted({x["source"] for x in result_jobs}), "warnings": warnings, "note": "Himalayas is remote-focused. Adzuna local/country listings require ADZUNA_APP_ID and ADZUNA_APP_KEY."}


@router.post("/api/saved-searches")
def save_search(payload: SaveSearchRequest, member: Member = Depends(current_member), db=Depends(get_db)):
    import json
    row = SavedSearch(member_id=member.id, name=payload.name.strip(), filters_json=payload.filters.model_dump_json())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "filters": json.loads(row.filters_json), "created_at": row.created_at.isoformat()}


@router.get("/api/saved-searches")
def list_saved_searches(member: Member = Depends(current_member), db=Depends(get_db)):
    import json
    rows = db.query(SavedSearch).filter(SavedSearch.member_id == member.id).order_by(SavedSearch.id.desc()).all()
    return [{"id": x.id, "name": x.name, "filters": json.loads(x.filters_json), "created_at": x.created_at.isoformat()} for x in rows]


@router.delete("/api/saved-searches/{search_id}")
def delete_saved_search(search_id: int, member: Member = Depends(current_member), db=Depends(get_db)):
    row = db.query(SavedSearch).filter(SavedSearch.id == search_id, SavedSearch.member_id == member.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Saved search not found.")
    db.delete(row)
    db.commit()
    return {"deleted": True, "id": search_id}
