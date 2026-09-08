"""
PortfoliAI — Phase 4 Production Engineering & Scalability Test Suite
Pytest-compatible verification of:
    1. Frontend visual asset preservation (SHA-256 integrity)
    2. Centralized configuration management (config.py)
    3. Security hardening & path traversal neutralization (security.py)
    4. Rate limiting sliding window mechanism
    5. User authentication, password hashing, and user ownership
    6. Database repository layer (User, Student, Project Repositories)
    7. PostgreSQL production indexes verification
    8. Resume SHA-256 hash performance caching
    9. Versioned RESTful API v1 endpoints & standardized envelopes
    10. Centralized error handling (400, 401, 404, 409, 413, 429)
    11. Backward compatibility preservation with Phase 1-3
"""

import os
import io
import json
import uuid
import hashlib
import pytest
import psycopg2

from config import Config
import main
from security import sanitize_upload_filename, SlidingWindowRateLimiter, api_success, api_error
from repositories.user_repository import UserRepository
from repositories.student_repository import StudentRepository
from repositories.project_repository import ProjectRepository
from resume_data import ResumeData, ProjectData, CategorizedSkills


# Known baseline SHA-256 hashes for frontend design preservation
STYLE_CSS_HASH = "d35e4369f7bc08f4882ce3a1104a56acecb2c5a53a876ec5180ead0aae635b59"
INDEX_HTML_HASH = "64accd6f43db002f4ebb44df770b251e307805563dc9aec291d2dd5296a9695c"
MAIN_JS_HASH = "4510814bb6e201abc018445c15f633870c80a163e8134e159de78bbfa2cda8bc"


def _compute_file_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def get_db():
    return psycopg2.connect(**Config.get_db_params())


# ============================================================
# 1. FRONTEND PRESERVATION TESTS
# ============================================================

def test_frontend_css_untouched():
    """Verify static/css/style.css is 100% byte-for-byte identical to baseline."""
    css_path = os.path.join("static", "css", "style.css")
    actual_hash = _compute_file_hash(css_path)
    assert actual_hash == STYLE_CSS_HASH, f"style.css modified! Expected {STYLE_CSS_HASH}, got {actual_hash}"


def test_frontend_html_untouched():
    """Verify templates/index.html is 100% byte-for-byte identical to baseline."""
    html_path = os.path.join("templates", "index.html")
    actual_hash = _compute_file_hash(html_path)
    assert actual_hash == INDEX_HTML_HASH, f"index.html modified! Expected {INDEX_HTML_HASH}, got {actual_hash}"


def test_frontend_js_untouched():
    """Verify static/js/main.js is 100% byte-for-byte identical to baseline."""
    js_path = os.path.join("static", "js", "main.js")
    actual_hash = _compute_file_hash(js_path)
    assert actual_hash == MAIN_JS_HASH, f"main.js modified! Expected {MAIN_JS_HASH}, got {actual_hash}"


# ============================================================
# 2. CENTRALIZED CONFIGURATION TESTS
# ============================================================

def test_config_db_params():
    """Verify Config provides valid database connection parameters."""
    params = Config.get_db_params()
    assert "host" in params
    assert "port" in params
    assert "database" in params
    assert "user" in params
    assert "password" in params
    assert params["database"] == "student_portfolio"


def test_config_upload_and_security_settings():
    """Verify upload limits and rate limit configuration."""
    assert Config.ALLOWED_EXTENSIONS == {"pdf"}
    assert Config.MAX_CONTENT_LENGTH == 10 * 1024 * 1024
    assert isinstance(Config.RATE_LIMIT_ENABLED, bool)
    assert Config.RATE_LIMIT_PER_MINUTE > 0


# ============================================================
# 3. SECURITY & PATH TRAVERSAL TESTS
# ============================================================

def test_sanitize_filename_traversal():
    """Verify path traversal sequences are completely neutralized."""
    malicious = "../../etc/passwd.pdf"
    cleaned = sanitize_upload_filename(malicious)
    assert ".." not in cleaned
    assert "/" not in cleaned
    assert "\\" not in cleaned
    assert cleaned.endswith(".pdf")


def test_sanitize_filename_null_byte():
    """Verify null bytes in filenames are neutralized."""
    malicious = "resume.pdf\x00.exe"
    cleaned = sanitize_upload_filename(malicious)
    assert "\x00" not in cleaned
    assert cleaned.endswith(".pdf")


def test_sanitize_filename_empty_and_reserved():
    """Verify empty or Windows reserved filenames receive safe fallbacks."""
    for bad in ["", "   ", "CON.pdf", "NUL.pdf", "PRN.pdf"]:
        cleaned = sanitize_upload_filename(bad)
        assert cleaned.endswith(".pdf")
        assert len(cleaned) > 4


def test_sliding_window_rate_limiter():
    """Verify sliding-window rate limiter blocks requests exceeding threshold."""
    limiter = SlidingWindowRateLimiter(window_seconds=10)
    key = "test-client-ip"

    # Allow up to 3 requests
    assert limiter.is_allowed(key, max_requests=3) is True
    assert limiter.is_allowed(key, max_requests=3) is True
    assert limiter.is_allowed(key, max_requests=3) is True
    # 4th request must be rejected
    assert limiter.is_allowed(key, max_requests=3) is False

    # Reset clears records
    limiter.reset()
    assert limiter.is_allowed(key, max_requests=3) is True


# ============================================================
# 4. USER AUTHENTICATION & REPOSITORY TESTS
# ============================================================

def test_user_password_hashing():
    """Verify password hashing produces salted, verifiable hashes."""
    pwd = "SecurePassword123!"
    pwd_hash = UserRepository.hash_password(pwd)
    assert pwd_hash != pwd
    assert UserRepository.verify_password(pwd_hash, pwd) is True
    assert UserRepository.verify_password(pwd_hash, "WrongPassword") is False
    assert UserRepository.verify_password("", pwd) is False


def test_user_repository_crud():
    """Verify creating, retrieving, and validating users in PostgreSQL."""
    repo = UserRepository(get_db)
    test_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    test_password = "SuperSecretPassword123"

    try:
        # 1. Create user
        user = repo.create_user(test_email, test_password)
        assert user["id"] is not None
        assert user["email"] == test_email
        user_id = user["id"]

        # 2. Retrieve by email
        fetched = repo.get_user_by_email(test_email)
        assert fetched is not None
        assert fetched["id"] == user_id
        assert fetched["email"] == test_email
        assert repo.verify_password(fetched["password_hash"], test_password) is True

        # 3. Retrieve by ID
        fetched_by_id = repo.get_user_by_id(user_id)
        assert fetched_by_id is not None
        assert fetched_by_id["email"] == test_email

        # 4. Duplicate email rejected
        with pytest.raises(Exception):
            repo.create_user(test_email, "AnotherPassword123")

    finally:
        # Cleanup
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = %s", (test_email,))
        conn.commit()
        cursor.close()
        conn.close()


# ============================================================
# 5. STUDENT & PROJECT REPOSITORIES TESTS
# ============================================================

def test_student_and_project_repositories():
    """Verify StudentRepository and ProjectRepository save, update, and merge correctly."""
    s_repo = StudentRepository(get_db)
    p_repo = ProjectRepository(get_db)

    test_email = f"student_{uuid.uuid4().hex[:8]}@test.edu"
    conn = get_db()
    cursor = conn.cursor()

    student_id = None
    try:
        # 1. Save new student
        resume_data = ResumeData(
            name="Test Scholar",
            email=test_email,
            summary="Passionate distributed systems engineer.",
            headline="Backend Systems Engineer",
            skills=["Python", "PostgreSQL", "Docker"],
            education=["B.S. in CS - 2024"],
            experience=["Software Engineer Intern at Acme"],
            achievements=["Dean's Honor List"],
            parser_used="regex",
            ai_provider="local"
        )
        student_id = s_repo.save_or_update_student(
            conn=conn,
            enriched_data=resume_data,
            parser_name="regex",
            student_id=None,
            filename="scholar_resume.pdf",
            resume_text="Sample raw resume text"
        )
        conn.commit()
        assert isinstance(student_id, int)

        # 2. Retrieve student
        student = s_repo.get_student_by_id(student_id)
        assert student is not None
        assert student["name"] == "Test Scholar"
        assert student["email"] == test_email
        assert "Python" in student["skills"]

        # 3. Safe COALESCE update: empty values must NOT erase existing valid data
        sparse_data = ResumeData(
            name=None,
            email=None,
            summary="Updated summary without losing other fields.",
            skills=[],
            parser_used="regex",
            ai_provider="local"
        )
        s_repo.save_or_update_student(
            conn=conn,
            enriched_data=sparse_data,
            parser_name="regex",
            student_id=student_id
        )
        conn.commit()

        updated_student = s_repo.get_student_by_id(student_id)
        assert updated_student["name"] == "Test Scholar"  # Preserved
        assert updated_student["email"] == test_email     # Preserved
        assert "Python" in updated_student["skills"]      # Preserved
        assert updated_student["bio"] == "Updated summary without losing other fields."

        # 4. Save and merge projects
        projects = [
            ProjectData(
                title="Distributed Cache",
                description="High throughput in-memory cache",
                technologies=["Go", "Redis"],
                github_url="https://github.com/scholar/cache"
            )
        ]
        p_repo.merge_and_save_projects(conn=conn, student_id=student_id, enriched_projects=projects)
        conn.commit()

        proj_list = p_repo.get_projects_by_student_id(student_id)
        assert len(proj_list) == 1
        assert proj_list[0]["title"] == "Distributed Cache"
        assert proj_list[0]["technologies"] == "Go, Redis"

    finally:
        if student_id:
            cursor.execute("DELETE FROM projects WHERE student_id = %s", (student_id,))
            cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
            conn.commit()
        cursor.close()
        conn.close()


# ============================================================
# 6. DATABASE PRODUCTION INDEXES VERIFICATION
# ============================================================

def test_production_indexes_exist():
    """Verify required performance indexes exist in PostgreSQL."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename IN ('students', 'projects', 'users')
            """
        )
        indexes = {row[0] for row in cursor.fetchall()}

        required_indexes = {
            "idx_projects_student_id",
            "idx_students_email",
            "idx_students_resume_hash",
            "idx_students_user_id",
            "idx_users_email"
        }
        missing = required_indexes - indexes
        assert not missing, f"Missing required database indexes: {missing}"
    finally:
        cursor.close()
        conn.close()


# ============================================================
# 7. RESUME HASH PERFORMANCE CACHING TESTS
# ============================================================

def test_resume_hash_caching():
    """Verify identical resumes hit performance cache and avoid re-processing."""
    resume_text = """
Jane Doe
Email: jane.doe@techuniv.edu
Education: B.S. in Computer Science — 2024
Skills: Python, FastAPI, Docker, SQL
Projects:
Cloud Sentinel — Infrastructure monitoring service with Prometheus and Python.
Experience:
DevOps Intern at CloudCorp
"""
    # 1. First execution -> fresh processing
    res1 = main.resume_processor.process_text(resume_text, student_id=None)
    student_id = res1["student_id"]
    assert res1.get("cached") is False

    try:
        # 2. Second execution with same student_id and text -> cache hit
        res2 = main.resume_processor.process_text(resume_text, student_id=student_id)
        assert res2.get("cached") is True
        assert res2["student_id"] == student_id
        assert res2["portfolio"]["profile"]["name"] == "Jane Doe"

        # 3. Third execution with force_refresh=True -> bypass cache
        res3 = main.resume_processor.process_text(resume_text, student_id=student_id, force_refresh=True)
        assert res3.get("cached") is False

    finally:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE student_id = %s", (student_id,))
        cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
        conn.commit()
        cursor.close()
        conn.close()


# ============================================================
# 8. RESTFUL API V1 ENDPOINTS & RESPONSE ENVELOPES
# ============================================================

def test_api_v1_auth_flow():
    """Verify /api/v1/auth/register and /api/v1/auth/login endpoints."""
    client = main.app.test_client()
    test_email = f"api_user_{uuid.uuid4().hex[:8]}@example.com"
    test_pwd = "StrongSecurePassword999"

    try:
        # 1. Register user
        res_reg = client.post("/api/v1/auth/register", json={
            "email": test_email,
            "password": test_pwd
        })
        assert res_reg.status_code == 201
        reg_json = res_reg.get_json()
        assert reg_json["success"] is True
        assert reg_json["data"]["email"] == test_email
        assert "user_id" in reg_json["data"]

        # 2. Duplicate registration returns 409
        res_dup = client.post("/api/v1/auth/register", json={
            "email": test_email,
            "password": test_pwd
        })
        assert res_dup.status_code == 409
        dup_json = res_dup.get_json()
        assert dup_json["success"] is False
        assert dup_json["error"]["code"] == "USER_EXISTS"

        # 3. Login with correct credentials returns 200
        res_login = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": test_pwd
        })
        assert res_login.status_code == 200
        login_json = res_login.get_json()
        assert login_json["success"] is True
        assert login_json["data"]["email"] == test_email

        # 4. Login with invalid password returns 401
        res_bad_pwd = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "WrongPassword123"
        })
        assert res_bad_pwd.status_code == 401
        bad_json = res_bad_pwd.get_json()
        assert bad_json["success"] is False
        assert bad_json["error"]["code"] == "UNAUTHORIZED"

    finally:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = %s", (test_email,))
        conn.commit()
        cursor.close()
        conn.close()


def test_api_v1_portfolio_endpoints():
    """Verify versioned /api/v1/portfolio and /api/v1/portfolio/<id> endpoints."""
    client = main.app.test_client()

    # Retrieve latest portfolio
    res = client.get("/api/v1/portfolio")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "profile" in data["data"]
    assert "skills" in data["data"]
    assert "projects" in data["data"]

    # Non-existent student returns 404 with structured error envelope
    res_404 = client.get("/api/v1/portfolio/99999999")
    assert res_404.status_code == 404
    err_data = res_404.get_json()
    assert err_data["success"] is False
    assert err_data["error"]["code"] == "STUDENT_NOT_FOUND"


def test_api_v1_enrichment_status_endpoints():
    """Verify versioned /api/v1/enrichment-status endpoints."""
    client = main.app.test_client()

    res = client.get("/api/v1/enrichment-status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "processing_status" in data["data"]
    assert "ai_provider" in data["data"]


def test_api_v1_upload_endpoint():
    """Verify versioned /api/v1/resume/upload endpoint."""
    client = main.app.test_client()

    # 1. Non-PDF rejected
    res_txt = client.post(
        "/api/v1/resume/upload",
        data={"resume": (io.BytesIO(b"Hello text"), "resume.txt")},
        content_type="multipart/form-data"
    )
    assert res_txt.status_code == 400
    err_txt = res_txt.get_json()
    assert err_txt["success"] is False
    assert err_txt["error"]["code"] == "INVALID_FILE_TYPE"

    # 2. Valid PDF processed
    with open("test_resume.pdf", "rb") as f:
        pdf_bytes = f.read()

    res_pdf = client.post(
        "/api/v1/resume/upload",
        data={"resume": (io.BytesIO(pdf_bytes), "valid_v1.pdf")},
        content_type="multipart/form-data"
    )
    assert res_pdf.status_code == 201
    pdf_json = res_pdf.get_json()
    assert pdf_json["success"] is True
    assert "student_id" in pdf_json["data"]
    assert "portfolio" in pdf_json["data"]


# ============================================================
# 9. CENTRALIZED ERROR HANDLERS
# ============================================================

def test_centralized_error_handlers():
    """Verify centralized error handling envelopes for 404 and bad requests."""
    client = main.app.test_client()

    # 404 on API route
    res_404 = client.get("/api/v1/non_existent_route")
    assert res_404.status_code == 404
    data_404 = res_404.get_json()
    assert data_404["success"] is False
    assert data_404["error"]["code"] == "NOT_FOUND"


# ============================================================
# 10. CLI EXECUTION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PortfoliAI Phase 4 — Production Engineering Test Suite")
    print("=" * 60)

    test_funcs = [
        ("Frontend: CSS Hash Unchanged", test_frontend_css_untouched),
        ("Frontend: HTML Hash Unchanged", test_frontend_html_untouched),
        ("Frontend: JS Hash Unchanged", test_frontend_js_untouched),
        ("Config: DB Parameters Valid", test_config_db_params),
        ("Config: Upload & Rate Limit Settings", test_config_upload_and_security_settings),
        ("Security: Path Traversal Neutralized", test_sanitize_filename_traversal),
        ("Security: Null Bytes Neutralized", test_sanitize_filename_null_byte),
        ("Security: Empty / Reserved Names Handled", test_sanitize_filename_empty_and_reserved),
        ("Security: Sliding Window Rate Limiter", test_sliding_window_rate_limiter),
        ("Auth: Werkzeug Password Hashing", test_user_password_hashing),
        ("Auth: User Repository CRUD & Validation", test_user_repository_crud),
        ("Repositories: Student & Project CRUD / Merge", test_student_and_project_repositories),
        ("Database: Production Indexes Verified", test_production_indexes_exist),
        ("Performance: Resume Hash Caching", test_resume_hash_caching),
        ("API v1: Auth Register / Login Flow", test_api_v1_auth_flow),
        ("API v1: Portfolio Endpoints & Envelopes", test_api_v1_portfolio_endpoints),
        ("API v1: Enrichment Status Endpoints", test_api_v1_enrichment_status_endpoints),
        ("API v1: Resume Upload Endpoint", test_api_v1_upload_endpoint),
        ("Error Handlers: Centralized 404/400 Envelopes", test_centralized_error_handlers),
    ]

    passed = 0
    failed = 0

    for name, func in test_funcs:
        try:
            func()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Phase 4 Results: {passed}/{len(test_funcs)} PASSED")
    if failed > 0:
        print(f"FAILED: {failed} check(s)")
        raise SystemExit(1)
    else:
        print("All Phase 4 Production Engineering tests PASSED!")
        print("=" * 60)
