COMMON_SKILLS = {
    "python", "java", "javascript", "typescript", "react", "node.js",
    "fastapi", "django", "sql", "postgresql", "mysql", "mongodb",
    "docker", "kubernetes", "aws", "azure", "git", "github",
    "machine learning", "data analysis", "rest api"
}

def extract_skills(text: str) -> list[str]:
    text = text.lower()
    return sorted(skill for skill in COMMON_SKILLS if skill in text)
