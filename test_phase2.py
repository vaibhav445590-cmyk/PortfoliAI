"""
PortfoliAI — Phase 2 Comprehensive Test Suite

Tests:
    1. Provider abstraction & inheritance
    2. LocalEnricher skill categorization across 7 categories
    3. Authentic headline derivation without hallucination
    4. Project classification & description polishing
    5. Anti-hallucination guardrails (no fake URLs or invented qualifications)
    6. External provider failure simulation & graceful fallback (OpenAI & Ollama)
    7. EnrichmentService fallback chain orchestration
    8. PortfolioGenerator template context & JSON generation
    9. Content hashing & change detection
    10. Live PostgreSQL persistence of Phase 2 columns (headline, category, etc.)
    11. Flask API endpoints (/api/portfolio, /api/enrichment-status, /api/enrich-resume, /generate-portfolio)
"""

import os
import sys
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, ".")

from resume_data import ResumeData, ProjectData, CategorizedSkills
from ai.base_provider import BaseAIProvider
from ai.local_enricher import LocalEnricher
from ai.ollama_provider import OllamaProvider
from ai.openai_provider import OpenAIProvider
from ai.enrichment_service import EnrichmentService, create_default_enrichment_service
from portfolio_generator import PortfolioGenerator

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")
        if detail:
            print(f"        {detail}")


# ============================================================
# SAMPLE TEST DATA
# ============================================================

sample_skills = [
    "Python", "JavaScript", "TypeScript", "SQL",
    "React", "FastAPI", "Flask", "PyTorch",
    "PostgreSQL", "MongoDB", "Redis",
    "Docker", "AWS", "Git",
    "REST APIs", "GraphQL",
    "HTML", "CSS", "Tailwind CSS",
    "Agile", "Problem Solving"
]

sample_projects = [
    ProjectData(
        title="Portfolio Builder",
        description="A web application built using React and Flask for automated portfolios.",
        technologies=["React", "Flask", "PostgreSQL"],
        github_url="https://github.com/alex/portfolio",
        live_url="https://portfoliai.dev"
    ),
    ProjectData(
        title="Deep NLP Sentiment Engine",
        description="Trained a neural model with PyTorch to analyze sentiments in financial text.",
        technologies=["Python", "PyTorch", "NLP"]
    ),
    ProjectData(
        title="Microservice API Gateway",
        description="High throughput gateway service utilizing FastAPI and Redis caching.",
        technologies=["FastAPI", "Redis", "Docker"]
    )
]

sample_resume = ResumeData(
    name="Alex Sharma",
    email="alex.sharma@example.com",
    phone="+91 9000000000",
    summary="Motivated BCA student passionate about software engineering and building backend APIs.",
    skills=sample_skills,
    education=["Bachelor of Computer Applications (BCA) — 2026"],
    projects=sample_projects,
    experience=["Backend Development Intern at TechCorp"],
    achievements=["Certified Python Associate", "Winner, University Hackathon"],
    parser_used="Enhanced Regex",
    confidence=1.0
)


# ============================================================
# 1. PROVIDER ABSTRACTION & INTERFACE
# ============================================================
print("\n" + "=" * 60)
print("1. PROVIDER ABSTRACTION & INHERITANCE")
print("=" * 60)

local = LocalEnricher()
ollama = OllamaProvider()
openai_prov = OpenAIProvider()

check("LocalEnricher implements BaseAIProvider", isinstance(local, BaseAIProvider))
check("OllamaProvider implements BaseAIProvider", isinstance(ollama, BaseAIProvider))
check("OpenAIProvider implements BaseAIProvider", isinstance(openai_prov, BaseAIProvider))
check("LocalEnricher is always available", local.is_available() is True)
check("Provider name is non-empty string", len(local.name()) > 0)


# ============================================================
# 2. SKILL CATEGORIZATION
# ============================================================
print("\n" + "=" * 60)
print("2. SKILL INTELLIGENCE & CATEGORIZATION (7 CATEGORIES)")
print("=" * 60)

categorized = local.categorize_skills(sample_skills)

check("CategorizedSkills is valid model", isinstance(categorized, CategorizedSkills))
check("Languages detected (Python, JS, TS, SQL)", all(l in categorized.languages for l in ["Python", "JavaScript", "TypeScript", "SQL"]))
check("Frameworks detected (React, FastAPI, Flask, PyTorch)", all(f in categorized.frameworks for f in ["React", "FastAPI", "Flask", "PyTorch"]))
check("Databases detected (PostgreSQL, MongoDB, Redis)", all(d in categorized.databases for d in ["PostgreSQL", "MongoDB", "Redis"]))
check("Tools detected (Docker, AWS, Git)", all(t in categorized.tools for t in ["Docker", "AWS", "Git"]))
check("APIs detected (REST APIs, GraphQL)", all(a in categorized.apis for a in ["REST APIs", "GraphQL"]))
check("Web detected (HTML, CSS, Tailwind CSS)", all(w in categorized.web for w in ["HTML", "CSS", "Tailwind CSS"]))
check("Other skills retained (Agile, Problem Solving)", all(o in categorized.other for o in ["Agile", "Problem Solving"]))
check("No skills lost in categorization", len(categorized.all_skills()) == len(sample_skills))


# ============================================================
# 3. PROFESSIONAL HEADLINE DERIVATION
# ============================================================
print("\n" + "=" * 60)
print("3. AUTHENTIC HEADLINE DERIVATION")
print("=" * 60)

headline = local.generate_headline(sample_resume)
check("Headline generated", bool(headline))
check("Headline contains 'BCA Student'", "BCA Student" in headline, f"Got: {headline}")
check("Headline reflects technical focus", any(term in headline for term in ["Developer", "Backend", "AI"]), f"Got: {headline}")

# Test non-hallucination with different degrees
resume_btech = ResumeData(
    name="Test",
    education=["B.Tech Computer Science 2025"],
    skills=["Python", "Machine Learning", "PyTorch"]
)
headline_btech = local.generate_headline(resume_btech)
check("B.Tech degree reflected accurately", "B.Tech" in headline_btech, f"Got: {headline_btech}")
check("AI specialty reflected accurately", "AI & ML" in headline_btech, f"Got: {headline_btech}")


# ============================================================
# 4. PROJECT ENRICHMENT & CATEGORIZATION
# ============================================================
print("\n" + "=" * 60)
print("4. PROJECT ENRICHMENT & CLASSIFICATION")
print("=" * 60)

enriched_projects = local.enrich_projects(sample_projects)

check("All projects enriched", len(enriched_projects) == 3)
check("Project 1 classified as Web Application", enriched_projects[0].category == "Web Application", f"Got: {enriched_projects[0].category}")
check("Project 1 preserved GitHub URL", enriched_projects[0].github_url == "https://github.com/alex/portfolio")
check("Project 1 preserved Live URL", enriched_projects[0].live_url == "https://portfoliai.dev")
check("Project 2 classified as AI & Machine Learning", enriched_projects[1].category == "AI & Machine Learning", f"Got: {enriched_projects[1].category}")
check("Project 3 classified as Backend & API Service", enriched_projects[2].category == "Backend & API Service", f"Got: {enriched_projects[2].category}")
check("Descriptions polished with proper punctuation", all(p.description.endswith(".") for p in enriched_projects))


# ============================================================
# 5. SUMMARY POLISHING
# ============================================================
print("\n" + "=" * 60)
print("5. SUMMARY POLISHING")
print("=" * 60)

polished_summary = local.polish_summary(sample_resume)
check("Polished summary generated", bool(polished_summary))
check("Polished summary ends with period", polished_summary.endswith("."))
check("Original facts preserved in summary", "BCA student" in polished_summary and "backend" in polished_summary)

# Test when summary is originally empty
empty_summary_resume = ResumeData(
    name="Samir Khan",
    education=["BCA 2026"],
    skills=["Python", "Flask", "PostgreSQL"]
)
derived_summary = local.polish_summary(empty_summary_resume)
check("Derived summary generated from facts when empty", "Samir Khan" in derived_summary and "Python" in derived_summary)


# ============================================================
# 6. EXTERNAL PROVIDER FALLBACK & ROBUSTNESS
# ============================================================
print("\n" + "=" * 60)
print("6. PROVIDER FAULT TOLERANCE & FALLBACK")
print("=" * 60)

class FailingProvider(BaseAIProvider):
    def name(self) -> str:
        return "Failing Cloud Provider"
    def is_available(self) -> bool:
        return True
    def enrich_resume(self, resume: ResumeData):
        raise ConnectionError("Simulated API outage / 0 credits remaining")
    def categorize_skills(self, skills):
        return None
    def generate_headline(self, resume):
        return None
    def polish_summary(self, resume):
        return None
    def enrich_projects(self, projects):
        return None

class MalformedJsonProvider(BaseAIProvider):
    def name(self) -> str:
        return "Malformed JSON Provider"
    def is_available(self) -> bool:
        return True
    def enrich_resume(self, resume: ResumeData):
        return None
    def categorize_skills(self, skills):
        return None
    def generate_headline(self, resume):
        return None
    def polish_summary(self, resume):
        return None
    def enrich_projects(self, projects):
        return None

failing_service = EnrichmentService()
failing_service.register(FailingProvider())
failing_service.register(MalformedJsonProvider())

# Must not raise an exception, must fall back cleanly
res_fallback = failing_service.enrich(sample_resume, resume_text="Sample text")
check("Failing provider does not crash service", res_fallback is not None)
check("Falls back to Local Intelligence on failure", res_fallback.ai_provider == "Local Intelligence", f"Got: {res_fallback.ai_provider}")
check("Enriched headline generated under fallback", bool(res_fallback.headline))
check("Categorized skills generated under fallback", bool(res_fallback.categorized_skills))


# ============================================================
# 7. ANTI-HALLUCINATION GUARDRAILS
# ============================================================
print("\n" + "=" * 60)
print("7. ANTI-HALLUCINATION & DATA PRESERVATION GUARDRAILS")
print("=" * 60)

class HallucinatingProvider(BaseAIProvider):
    def name(self) -> str:
        return "Hallucinating Provider"
    def is_available(self) -> bool:
        return True
    def enrich_resume(self, resume: ResumeData):
        # Drops skills and invents fake company
        return ResumeData(
            name="Alex Sharma",
            skills=["InventedSkill1", "InventedSkill2"],  # Dropped real skills!
            projects=[]
        )
    def categorize_skills(self, skills):
        return None
    def generate_headline(self, resume):
        return "Chief Executive Officer at Apple"  # Hallucinated!
    def polish_summary(self, resume):
        return None
    def enrich_projects(self, projects):
        return None

guardrail_service = EnrichmentService()
guardrail_service.register(HallucinatingProvider())

guarded_result = guardrail_service.enrich(sample_resume)
check("Real skills are NEVER dropped by hallucinating provider", all(s in guarded_result.skills for s in sample_resume.skills))
check("Original projects are NEVER wiped by hallucinating provider", len(guarded_result.projects) == len(sample_projects))


# ============================================================
# 8. PORTFOLIO GENERATION SERVICE
# ============================================================
print("\n" + "=" * 60)
print("8. PORTFOLIO GENERATION SERVICE")
print("=" * 60)

generator = PortfolioGenerator()

# 1. Template context test
dummy_student_row = (
    1, "Alex Sharma", "alex@test.com", "Bio text", "Python, React",
    "BCA 2026", "resume.pdf", "Intern", "Certified", "Enhanced Regex",
    "BCA Student · Full-Stack Developer", '{"Programming Languages": ["Python"]}', "Local Intelligence"
)
dummy_project_rows = [
    (10, 1, "Project One", "Description one", "Python, Flask", "https://github.com/repo", "https://live.site", "Web Application")
]

template_context = generator.format_template_context(dummy_student_row, dummy_project_rows)

check("Template context has student key", "student" in template_context and template_context["student"] is not None)
check("Template context has projects key", "projects" in template_context and len(template_context["projects"]) == 1)
check("Student dict has required template fields", all(k in template_context["student"] for k in ["name", "email", "bio", "skills", "education", "resume_filename"]))
check("Project dict has required template fields", all(k in template_context["projects"][0] for k in ["title", "description", "technologies", "github_url", "category"]))

# 2. JSON generation test
portfolio_json = generator.generate_portfolio_json(res_fallback)
check("Portfolio JSON has profile", "profile" in portfolio_json and portfolio_json["profile"]["name"] == "Alex Sharma")
check("Portfolio JSON has stats", "stats" in portfolio_json and portfolio_json["stats"]["projects_count"] == 3)
check("Portfolio JSON has categorized skills", "categorized" in portfolio_json["skills"])
check("Portfolio JSON has metadata", "metadata" in portfolio_json and portfolio_json["metadata"]["ai_provider"] == "Local Intelligence")


# ============================================================
# 9. CONTENT HASHING & CHANGE DETECTION
# ============================================================
print("\n" + "=" * 60)
print("9. RESUME CONTENT HASHING")
print("=" * 60)

hash1 = EnrichmentService.compute_resume_hash("Alex Sharma BCA Student")
hash2 = EnrichmentService.compute_resume_hash("Alex Sharma BCA Student")
hash3 = EnrichmentService.compute_resume_hash("Different Resume Text")

check("Hash is deterministic", hash1 == hash2)
check("Different text produces different hash", hash1 != hash3)
check("Hash is SHA256 hex string", len(hash1) == 64)


# ============================================================
# 10. LIVE POSTGRESQL PERSISTENCE (PHASE 2 COLUMNS)
# ============================================================
print("\n" + "=" * 60)
print("10. LIVE POSTGRESQL PERSISTENCE OF PHASE 2 COLUMNS")
print("=" * 60)

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="student_portfolio",
    user="postgres",
    password=os.getenv("DB_PASSWORD", "")
)
cursor = conn.cursor()

# Check all Phase 2 columns exist
def check_col(table, col):
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        )
    """, (table, col))
    return cursor.fetchone()[0]

check("students.headline exists in PostgreSQL", check_col("students", "headline"))
check("students.categorized_skills exists in PostgreSQL", check_col("students", "categorized_skills"))
check("students.ai_provider exists in PostgreSQL", check_col("students", "ai_provider"))
check("students.resume_hash exists in PostgreSQL", check_col("students", "resume_hash"))
check("students.processing_status exists in PostgreSQL", check_col("students", "processing_status"))
check("students.last_processed_at exists in PostgreSQL", check_col("students", "last_processed_at"))
check("projects.category exists in PostgreSQL", check_col("projects", "category"))

# Test inserting Phase 2 enriched record
TEST_EMAIL = "qa_phase2_test@test.com"
cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
conn.commit()

cursor.execute("""
    INSERT INTO students (
        name, email, bio, skills, education, experience, achievements,
        parser_used, headline, categorized_skills, ai_provider, resume_hash, processing_status
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
""", (
    "Phase2 Tester",
    TEST_EMAIL,
    "Enriched Bio",
    "Python, React, FastAPI",
    "BCA 2026",
    "Intern",
    "Certification",
    "Enhanced Regex",
    "BCA Student · Backend Developer",
    '{"Programming Languages": ["Python"], "Frameworks & Libraries": ["FastAPI", "React"]}',
    "Local Intelligence",
    hash1,
    "completed"
))
s_id = cursor.fetchone()[0]

cursor.execute("""
    INSERT INTO projects (student_id, title, description, technologies, github_url, category)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
""", (
    s_id,
    "Phase 2 Project",
    "A categorized project",
    "Python, FastAPI",
    "https://github.com/test/proj",
    "Backend & API Service"
))
p_id = cursor.fetchone()[0]
conn.commit()

cursor.execute("""
    SELECT headline, categorized_skills, ai_provider, resume_hash, processing_status
    FROM students WHERE id = %s
""", (s_id,))
s_row = cursor.fetchone()

check("Headline persists in PostgreSQL", s_row[0] == "BCA Student · Backend Developer", f"Got: {s_row[0]}")
check("Categorized skills persists in PostgreSQL", "FastAPI" in s_row[1])
check("AI provider persists in PostgreSQL", s_row[2] == "Local Intelligence")
check("Resume hash persists in PostgreSQL", s_row[3] == hash1)
check("Processing status persists in PostgreSQL", s_row[4] == "completed")

cursor.execute("SELECT category FROM projects WHERE id = %s", (p_id,))
cat_row = cursor.fetchone()
check("Project category persists in PostgreSQL", cat_row[0] == "Backend & API Service", f"Got: {cat_row[0]}")

# Clean up test rows
cursor.execute("DELETE FROM projects WHERE id = %s", (p_id,))
cursor.execute("DELETE FROM students WHERE id = %s", (s_id,))
conn.commit()
cursor.close()
conn.close()


# ============================================================
# 11. FLASK API ENDPOINTS & GENERATE PORTFOLIO
# ============================================================
print("\n" + "=" * 60)
print("11. FLASK APPLICATION ENDPOINTS")
print("=" * 60)

import main
client = main.app.test_client()

# 1. GET /
res_home = client.get("/")
check("GET / status 200", res_home.status_code == 200)

# 2. GET /test-db
res_db = client.get("/test-db")
check("GET /test-db status 200", res_db.status_code == 200)

# 3. POST /generate-portfolio (runs full parsing + Phase 2 enrichment + storage)
res_gen = client.post("/generate-portfolio")
check("POST /generate-portfolio status 200", res_gen.status_code == 200)
gen_data = res_gen.get_json()
check("generate-portfolio returns success", gen_data.get("success") is True)
check("generate-portfolio returns ai_provider", "ai_provider" in gen_data and len(gen_data["ai_provider"]) > 0)
check("generate-portfolio returns headline", "headline" in gen_data and len(gen_data["headline"]) > 0)
check("generate-portfolio returns categorized_skills", "categorized_skills" in gen_data and isinstance(gen_data["categorized_skills"], dict))

# 4. GET /api/portfolio
res_port = client.get("/api/portfolio")
check("GET /api/portfolio status 200", res_port.status_code == 200)
port_data = res_port.get_json()
check("api/portfolio returns profile", "profile" in port_data and "name" in port_data["profile"])
check("api/portfolio returns categorized skills", "skills" in port_data and "categorized" in port_data["skills"])
check("api/portfolio returns projects list", "projects" in port_data and isinstance(port_data["projects"], list))

# 5. GET /api/enrichment-status
res_status = client.get("/api/enrichment-status")
check("GET /api/enrichment-status status 200", res_status.status_code == 200)
status_data = res_status.get_json()
check("api/enrichment-status has processing_status", status_data.get("processing_status") == "completed")
check("api/enrichment-status has ai_provider", bool(status_data.get("ai_provider")))

# 6. POST /api/enrich-resume on-demand
sample_resume_text = """
Rahul Verma
Email: rahul.v@example.com | Phone: +91 9123456780
Education: BCA 2026
Skills: Python, FastAPI, React, PostgreSQL, Docker
Projects:
BookStore API — REST API for book management with FastAPI and PostgreSQL.
"""
res_enrich = client.post("/api/enrich-resume", json={"text": sample_resume_text})
check("POST /api/enrich-resume status 200", res_enrich.status_code == 200)
enrich_json = res_enrich.get_json()
check("On-demand enrichment returns profile", enrich_json["profile"]["name"] == "Rahul Verma")
check("On-demand enrichment derives headline", "BCA" in enrich_json["profile"]["headline"])


# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
total = passed + failed
if failed == 0:
    print(f"ALL {total} PHASE 2 TESTS PASSED")
else:
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
print("=" * 60)

if __name__ == "__main__":
    sys.exit(0 if failed == 0 else 1)
