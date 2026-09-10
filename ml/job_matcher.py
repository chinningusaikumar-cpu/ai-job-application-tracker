from skill_extractor import extract_skills

def calculate_match(resume_text: str, job_text: str) -> dict:
    resume_skills = set(extract_skills(resume_text))
    job_skills = set(extract_skills(job_text))

    if not job_skills:
        score = 0
    else:
        score = round(len(resume_skills & job_skills) / len(job_skills) * 100)

    return {
        "score": score,
        "matched_skills": sorted(resume_skills & job_skills),
        "missing_skills": sorted(job_skills - resume_skills),
    }
