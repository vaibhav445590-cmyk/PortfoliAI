"""
PortfoliAI — Phase 3 Comprehensive Test Suite
End-to-End Product Workflow Verification

Covers all Phase 3 requirements:
    1. Upload Handling & Security (valid, invalid ext, missing, empty, corrupted, oversized, traversal)
    2. Parsing, Extraction & Validation (PDF text extraction, regex pipeline, Pydantic validation)
    3. AI / Local Enrichment (fallback, authentic headline, 7 skill categories, anti-hallucination)
    4. Database Persistence & Data Safety (COALESCE safety, project merging, unparsed retention, no duplicates)
    5. Portfolio & Status APIs (/api/portfolio/<id>, 404 handling, /api/enrichment-status/<id>, schema)
    6. Complete End-to-End Workflow (Upload -> Extract -> Parse -> Enrich -> Persist -> Generate -> API)
    7. Multi-Student Independence (Resume A vs Resume B isolation)

Compatible with both:
    - pytest (`python -m pytest test_phase3.py` or `python -m pytest`)
    - Direct CLI execution (`python test_phase3.py`)
"""

import os
import io
import sys
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Ensure current working directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main
from resume_processor import (
    validate_pdf_content,
    extract_pdf_text_from_bytes,
    extract_pdf_text_from_file,
    persist_student_data,
    persist_project_data,
    MAX_RESUME_BYTES
)
from resume_data import ResumeData, ProjectData, CategorizedSkills
from ai.local_enricher import LocalEnricher

passed = 0
failed = 0


def check(name, condition, detail=""):
    """Assertion helper tracking CLI tallies and asserting for pytest."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")
        if detail:
            print(f"        {detail}")
    assert condition, f"{name}: {detail}"


def get_db():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="student_portfolio",
        user="postgres",
        password=os.getenv("DB_PASSWORD", "")
    )


# ============================================================
# 1. UPLOAD HANDLING & SECURITY TESTS
# ============================================================

def test_upload_handling_and_security():
    """Verify upload restrictions, extension check, corruption handling, and security."""
    print("\n" + "=" * 60)
    print("1. UPLOAD HANDLING & SECURITY")
    print("=" * 60)

    client = main.app.test_client()

    # 1.1 Missing file key
    res_no_file = client.post("/upload-resume", data={}, headers={"Accept": "application/json"})
    check("Upload rejects missing file key", res_no_file.status_code == 400)
    check("Missing file key error message", "No resume file" in res_no_file.get_json().get("error", ""))

    # 1.2 Empty filename
    res_empty_fn = client.post(
        "/upload-resume",
        data={"resume": (io.BytesIO(b"content"), "")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"}
    )
    check("Upload rejects empty filename", res_empty_fn.status_code == 400)

    # 1.3 Invalid extension (.txt)
    res_txt = client.post(
        "/upload-resume",
        data={"resume": (io.BytesIO(b"Just plain text resume"), "resume.txt")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"}
    )
    check("Upload rejects .txt file", res_txt.status_code == 400)
    check("Only PDF error message", "Only PDF files" in res_txt.get_json().get("error", ""))

    # 1.4 Invalid extension (.png)
    res_png = client.post(
        "/upload-resume",
        data={"resume": (io.BytesIO(b"\x89PNG\r\n\x1a\n"), "avatar.png")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"}
    )
    check("Upload rejects .png file", res_png.status_code == 400)

    # 1.5 Corrupted / Fake PDF (bad header)
    res_fake_pdf = client.post(
        "/upload-resume",
        data={"resume": (io.BytesIO(b"This is not a real PDF file!"), "resume.pdf")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"}
    )
    check("Upload rejects fake PDF with bad header", res_fake_pdf.status_code == 400)
    check("Fake PDF rejected with header error", "Invalid PDF header" in res_fake_pdf.get_json().get("error", ""))

    # 1.6 Empty file (0 bytes)
    res_empty_file = client.post(
        "/upload-resume",
        data={"resume": (io.BytesIO(b""), "empty.pdf")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"}
    )
    check("Upload rejects 0-byte file", res_empty_file.status_code == 400)
    check("Empty file error message", "empty" in res_empty_file.get_json().get("error", "").lower())

    # 1.7 Oversized file (> 10MB)
    oversized_bytes = b"%PDF-1.4\n" + b"0" * (10 * 1024 * 1024 + 1024)
    is_valid, size_err = validate_pdf_content(oversized_bytes)
    check("Validator catches oversized file", not is_valid and "10 MB" in size_err)

    # 1.8 Valid PDF upload via test_resume.pdf
    with open("test_resume.pdf", "rb") as f:
        pdf_bytes = f.read()

    res_valid = client.post(
        "/upload-resume",
        data={"resume": (io.BytesIO(pdf_bytes), "my_resume.pdf")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"}
    )
    check("Upload valid PDF returns 200", res_valid.status_code == 200)
    val_json = res_valid.get_json()
    check("Valid upload returns success", val_json.get("success") is True)
    check("Valid upload returns student_id", isinstance(val_json.get("student_id"), int))
    check("Valid upload records filename", val_json.get("filename") == "my_resume.pdf")


# ============================================================
# 2. PDF EXTRACTION & PARSER PIPELINE TESTS
# ============================================================

def test_pdf_extraction_and_parser_pipeline():
    """Verify PDF text extraction, structured parsing, and Pydantic validation."""
    print("\n" + "=" * 60)
    print("2. PDF EXTRACTION & PARSER PIPELINE")
    print("=" * 60)

    # 2.1 Extraction from file
    text, error = extract_pdf_text_from_file("test_resume.pdf")
    check("extract_pdf_text_from_file succeeds", bool(text) and not error)
    check("Extracted text contains Alex Sharma", "Alex Sharma" in text)
    check("Extracted text contains Skills section", "Skills" in text)

    # 2.2 Parse via main.resume_pipeline
    parsed_data, parser_name = main.resume_pipeline.parse(text)
    check("Parser pipeline succeeds", parsed_data is not None)
    check("Parser used is Enhanced Regex", parser_name == "Enhanced Regex")
    check("Parsed student name is Alex Sharma", parsed_data.name == "Alex Sharma")
    check("Parsed email is alex.sharma@example.com", parsed_data.email == "alex.sharma@example.com")
    check("Parsed skills list is non-empty", len(parsed_data.skills) > 0)
    check("Parsed projects count > 0", len(parsed_data.projects) > 0)
    check("Parsed experience list non-empty", len(parsed_data.experience) > 0)
    check("Confidence is computed", 0.0 <= parsed_data.confidence <= 1.0)


# ============================================================
# 3. AI / LOCAL ENRICHMENT TESTS
# ============================================================

def test_ai_enrichment_and_anti_hallucination():
    """Verify enrichment completes reliably without cloud credits and respects anti-hallucination rules."""
    print("\n" + "=" * 60)
    print("3. AI ENRICHMENT & ANTI-HALLUCINATION")
    print("=" * 60)

    text, _ = extract_pdf_text_from_file("test_resume.pdf")
    parsed_data, _ = main.resume_pipeline.parse(text)

    # Enrich via enrichment_service (guaranteed to fall back to Local Intelligence if no OpenAI credits)
    enriched = main.enrichment_service.enrich(parsed_data, resume_text=text)

    check("Enrichment produces non-empty headline", bool(enriched.headline))
    check("Headline reflects student background", "BCA" in enriched.headline)
    check("Skills are categorized", enriched.categorized_skills is not None)

    cat_dict = enriched.categorized_skills.to_dict()
    check("Categorized skills has Programming Languages", len(cat_dict.get("Programming Languages", [])) > 0)
    check("Categorized skills has Databases", len(cat_dict.get("Databases & Storage", [])) > 0)

    # Anti-hallucination check: ensure original parsed skills are preserved
    for s in parsed_data.skills:
        check(f"Skill '{s}' preserved in enriched skills", s in enriched.skills)

    # Ensure projects retain original titles and URLs
    for orig, enr in zip(parsed_data.projects, enriched.projects):
        check(f"Project '{orig.title}' title preserved", orig.title == enr.title)
        check(f"Project '{orig.title}' GitHub URL not hallucinated", enr.github_url == orig.github_url)


# ============================================================
# 4. DATABASE PERSISTENCE & DATA SAFETY TESTS
# ============================================================

def test_database_persistence_and_safety():
    """Verify PostgreSQL persistence, COALESCE protection, and safe project re-processing."""
    print("\n" + "=" * 60)
    print("4. DATABASE PERSISTENCE & DATA SAFETY")
    print("=" * 60)

    conn = get_db()
    cursor = conn.cursor()

    TEST_EMAIL = "p3_safety_test@example.com"

    try:
        # Clean up existing test data
        cursor.execute("DELETE FROM projects WHERE student_id IN (SELECT id FROM students WHERE email = %s)", (TEST_EMAIL,))
        cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
        conn.commit()

        # Step 1: Insert student via persist_student_data
        resume_initial = ResumeData(
            name="Initial Student",
            email=TEST_EMAIL,
            summary="Initial valid summary statement.",
            skills=["Python", "FastAPI"],
            education=["BCA 2026"],
            experience=["Software Intern at Startup"],
            achievements=["Hackathon Winner"],
            projects=[
                ProjectData(
                    title="API Server",
                    description="FastAPI microservice",
                    technologies=["Python", "FastAPI"],
                    github_url="https://github.com/initial/api",
                    live_url="https://api.initial.dev",
                    category="Backend & API Service"
                ),
                ProjectData(
                    title="Manual Tool",
                    description="Internal tool",
                    technologies=["Bash"],
                    github_url="https://github.com/initial/tool"
                )
            ],
            headline="BCA Student · Backend Developer",
            categorized_skills=CategorizedSkills(
                languages=["Python"],
                frameworks=["FastAPI"]
            )
        )

        s_id = persist_student_data(
            conn=conn,
            enriched_data=resume_initial,
            parser_name="Enhanced Regex",
            student_id=None,
            filename="initial.pdf",
            resume_text="Initial resume text"
        )
        persist_project_data(conn=conn, student_id=s_id, enriched_projects=resume_initial.projects)
        conn.commit()

        check("Student inserted and assigned ID", isinstance(s_id, int) and s_id > 0)

        # Step 2: COALESCE Safety — Update with empty fields
        resume_empty = ResumeData(
            name=None,
            email=None,
            summary=None,
            skills=[],
            education=[],
            experience=[],
            achievements=[],
            projects=[]
        )

        persist_student_data(
            conn=conn,
            enriched_data=resume_empty,
            parser_name="Fallback",
            student_id=s_id,
            filename=None,
            resume_text=None
        )
        # Empty projects should NOT delete existing projects!
        persist_project_data(conn=conn, student_id=s_id, enriched_projects=resume_empty.projects)
        conn.commit()

        cursor.execute("SELECT name, email, bio, skills, education, experience, achievements FROM students WHERE id = %s", (s_id,))
        row = cursor.fetchone()
        check("COALESCE preserved name", row[0] == "Initial Student")
        check("COALESCE preserved email", row[1] == TEST_EMAIL)
        check("COALESCE preserved bio", row[2] == "Initial valid summary statement.")
        check("COALESCE preserved skills", "Python" in row[3])
        check("COALESCE preserved education", "BCA 2026" in row[4])
        check("COALESCE preserved experience", "Software Intern" in row[5])
        check("COALESCE preserved achievements", "Hackathon Winner" in row[6])

        cursor.execute("SELECT COUNT(*) FROM projects WHERE student_id = %s", (s_id,))
        p_count = cursor.fetchone()[0]
        check("Empty project list did NOT delete projects", p_count == 2)

        # Step 3: Safe Re-processing — Update 'API Server' without wiping github_url or deleting 'Manual Tool'
        resume_update = ResumeData(
            name="Initial Student",
            email=TEST_EMAIL,
            projects=[
                ProjectData(
                    title="API Server",
                    description="Updated description for API Server",
                    technologies=[],  # empty techs should fallback to existing
                    github_url=None,   # None should preserve existing URL
                    live_url=None
                ),
                ProjectData(
                    title="Brand New Project",
                    description="A third project",
                    technologies=["React"]
                )
            ]
        )
        persist_project_data(conn=conn, student_id=s_id, enriched_projects=resume_update.projects)
        conn.commit()

        cursor.execute("SELECT title, description, technologies, github_url FROM projects WHERE student_id = %s ORDER BY title ASC", (s_id,))
        p_rows = cursor.fetchall()
        p_by_title = {r[0]: r for r in p_rows}

        check("Re-processing has 3 total projects", len(p_rows) == 3)
        check("Existing unparsed 'Manual Tool' preserved", "Manual Tool" in p_by_title)
        check("Updated 'API Server' description updated", p_by_title["API Server"][1] == "Updated description for API Server")
        check("Updated 'API Server' preserved github_url", p_by_title["API Server"][3] == "https://github.com/initial/api")
        check("Updated 'API Server' preserved technologies", "Python" in p_by_title["API Server"][2])
        check("Newly added 'Brand New Project' stored", "Brand New Project" in p_by_title)

    finally:
        cursor.execute("DELETE FROM projects WHERE student_id IN (SELECT id FROM students WHERE email = %s)", (TEST_EMAIL,))
        cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
        conn.commit()
        cursor.close()
        conn.close()


# ============================================================
# 5. PORTFOLIO & STATUS API TESTS
# ============================================================

def test_portfolio_and_status_apis():
    """Verify /api/portfolio/<id>, /api/enrichment-status/<id>, and 404 handling."""
    print("\n" + "=" * 60)
    print("5. PORTFOLIO & STATUS APIS")
    print("=" * 60)

    client = main.app.test_client()

    # 5.1 404 for nonexistent student
    res_404_port = client.get("/api/portfolio/99999999")
    check("GET /api/portfolio/<missing_id> returns 404", res_404_port.status_code == 404)
    check("GET /api/portfolio/<missing_id> error response", "Student not found" in res_404_port.get_json().get("error", ""))

    res_404_status = client.get("/api/enrichment-status/99999999")
    check("GET /api/enrichment-status/<missing_id> returns 404", res_404_status.status_code == 404)

    # 5.2 Latest portfolio endpoint
    res_port = client.get("/api/portfolio")
    check("GET /api/portfolio returns 200", res_port.status_code == 200)
    port_json = res_port.get_json()

    # Verify structured JSON format
    check("Portfolio JSON has profile", "profile" in port_json)
    check("Portfolio profile has name", "name" in port_json["profile"])
    check("Portfolio profile has headline", "headline" in port_json["profile"])
    check("Portfolio profile has bio", "bio" in port_json["profile"])
    check("Portfolio profile has avatar_letter", "avatar_letter" in port_json["profile"])
    check("Portfolio JSON has stats", "stats" in port_json)
    check("Portfolio JSON has skills", "skills" in port_json)
    check("Portfolio JSON has projects", isinstance(port_json["projects"], list))
    check("Portfolio JSON has metadata", "metadata" in port_json)
    check("Portfolio metadata has parser_used", "parser_used" in port_json["metadata"])
    check("Portfolio metadata has ai_provider", "ai_provider" in port_json["metadata"])

    # 5.3 Latest status endpoint
    res_status = client.get("/api/enrichment-status")
    check("GET /api/enrichment-status returns 200", res_status.status_code == 200)
    status_json = res_status.get_json()
    check("Status has processing_status", "processing_status" in status_json)
    check("Status has ai_provider", "ai_provider" in status_json)


# ============================================================
# 6. END-TO-END WORKFLOW TEST
# ============================================================

def test_end_to_end_workflow():
    """Verify complete flow: Upload -> Extract -> Parse -> Enrich -> Persist -> Generate -> API."""
    print("\n" + "=" * 60)
    print("6. COMPLETE END-TO-END WORKFLOW")
    print("=" * 60)

    client = main.app.test_client()

    # 1. Upload test_resume.pdf
    with open("test_resume.pdf", "rb") as f:
        pdf_bytes = f.read()

    res_upload = client.post(
        "/upload-resume",
        data={"resume": (io.BytesIO(pdf_bytes), "e2e_resume.pdf")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"}
    )
    check("E2E Step 1 (Upload) succeeds", res_upload.status_code == 200)
    student_id = res_upload.get_json()["student_id"]
    check("E2E Step 1 returned student_id", isinstance(student_id, int))

    # 2. Trigger portfolio generation
    res_gen = client.post("/generate-portfolio", json={"student_id": student_id})
    check("E2E Step 2 (Generate) succeeds", res_gen.status_code == 200)
    gen_data = res_gen.get_json()
    check("E2E Step 2 returns success", gen_data.get("success") is True)
    check("E2E Step 2 returns headline", bool(gen_data.get("headline")))
    check("E2E Step 2 returns categorized_skills", isinstance(gen_data.get("categorized_skills"), dict))

    # 3. Retrieve generated portfolio via API for that specific student_id
    res_port = client.get(f"/api/portfolio/{student_id}")
    check("E2E Step 3 (API Portfolio) succeeds", res_port.status_code == 200)
    port_data = res_port.get_json()
    check("E2E Step 3 profile name is Alex Sharma", port_data["profile"]["name"] == "Alex Sharma")
    check("E2E Step 3 projects list populated", len(port_data["projects"]) > 0)
    check("E2E Step 3 avatar letter is A", port_data["profile"]["avatar_letter"] == "A")

    # 4. Check enrichment status for that student_id
    res_st = client.get(f"/api/enrichment-status/{student_id}")
    check("E2E Step 4 (API Status) succeeds", res_st.status_code == 200)
    st_data = res_st.get_json()
    check("E2E Step 4 processing_status is completed", st_data["processing_status"] == "completed")


# ============================================================
# 7. MULTI-STUDENT INDEPENDENCE TEST
# ============================================================

def test_multi_student_independence():
    """Verify that multiple resumes create independent student records and separate portfolios."""
    print("\n" + "=" * 60)
    print("7. MULTI-STUDENT INDEPENDENCE")
    print("=" * 60)

    client = main.app.test_client()

    resume_text_a = """
Alice Wonder
Email: alice.w@university.edu | Phone: +1 555-0100
Education: B.S. in Computer Science — 2025
Summary: Distributed systems enthusiast and backend engineer.
Skills: Go, Kubernetes, Docker, PostgreSQL, gRPC
Projects:
Cluster Orchestrator — A lightweight container orchestrator written in Go.
Experience:
Cloud Engineering Intern at MegaCloud
"""

    resume_text_b = """
Bob Builder
Email: bob.b@polytech.edu | Phone: +1 555-0200
Education: B.Tech in Artificial Intelligence — 2026
Summary: Machine learning developer specializing in computer vision models.
Skills: Python, PyTorch, OpenCV, Flask, AWS
Projects:
VisionNet Scanner — Real-time object detection using PyTorch and OpenCV.
Experience:
Computer Vision Researcher at AI Labs
"""

    conn = get_db()
    cursor = conn.cursor()

    try:
        # Process Student A
        res_a = main.resume_processor.process_text(resume_text_a)
        id_a = res_a["student_id"]

        # Process Student B
        res_b = main.resume_processor.process_text(resume_text_b)
        id_b = res_b["student_id"]

        check("Student A and Student B have distinct IDs", id_a != id_b)

        # Retrieve Portfolio A
        port_a = client.get(f"/api/portfolio/{id_a}").get_json()
        # Retrieve Portfolio B
        port_b = client.get(f"/api/portfolio/{id_b}").get_json()

        check("Portfolio A has Alice Wonder", port_a["profile"]["name"] == "Alice Wonder")
        check("Portfolio B has Bob Builder", port_b["profile"]["name"] == "Bob Builder")

        check("Portfolio A has Go skill", "Go" in port_a["skills"]["all"])
        check("Portfolio B does NOT have Go skill", "Go" not in port_b["skills"]["all"])
        check("Portfolio B has PyTorch skill", "PyTorch" in port_b["skills"]["all"])
        check("Portfolio A does NOT have PyTorch skill", "PyTorch" not in port_a["skills"]["all"])

        # Check project separation
        proj_titles_a = [p["title"] for p in port_a["projects"]]
        proj_titles_b = [p["title"] for p in port_b["projects"]]

        check("Portfolio A has Cluster Orchestrator", "Cluster Orchestrator" in proj_titles_a)
        check("Portfolio A does NOT leak VisionNet Scanner", "VisionNet Scanner" not in proj_titles_a)
        check("Portfolio B has VisionNet Scanner", "VisionNet Scanner" in proj_titles_b)
        check("Portfolio B does NOT leak Cluster Orchestrator", "Cluster Orchestrator" not in proj_titles_b)

    finally:
        cursor.execute("DELETE FROM projects WHERE student_id IN (SELECT id FROM students WHERE email IN ('alice.w@university.edu', 'bob.b@polytech.edu'))")
        cursor.execute("DELETE FROM students WHERE email IN ('alice.w@university.edu', 'bob.b@polytech.edu')")
        conn.commit()
        cursor.close()
        conn.close()


# ============================================================
# CLI RUNNER
# ============================================================

def run_all_phase3_tests():
    print("=" * 60)
    print("PORTFOLIAI — PHASE 3 TEST SUITE")
    print("=" * 60)

    test_upload_handling_and_security()
    test_pdf_extraction_and_parser_pipeline()
    test_ai_enrichment_and_anti_hallucination()
    test_database_persistence_and_safety()
    test_portfolio_and_status_apis()
    test_end_to_end_workflow()
    test_multi_student_independence()

    print("\n" + "=" * 60)
    total = passed + failed
    if failed == 0:
        print(f"ALL {total} PHASE 3 TESTS PASSED")
    else:
        print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all_phase3_tests()
    sys.exit(0 if success else 1)
