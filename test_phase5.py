"""
PortfoliAI — Phase 5 User Workspace & Portfolio Customization Test Suite
Pytest-compatible verification of:
    1. User workspace profile (GET /api/v1/me)
    2. Resume metadata inspection and safe clearing (GET/DELETE /api/v1/resume)
    3. Project CRUD operations and URL validation (POST/GET/PUT/DELETE /api/v1/projects)
    4. Project ownership and multi-student isolation (User B cannot modify User A's project)
    5. Portfolio customization settings validation (template, theme, accent, status, section_visibility, project_order, social_links)
    6. Performance guarantee: Fast DB settings update with zero AI / parsing rerun
    7. Draft mode protection vs. published public visibility
    8. Preview mode endpoint (GET /api/v1/portfolio/me/preview)
    9. Custom field overlay in portfolio generator and template context
    10. Frontend frozen design integrity (SHA-256 validation)
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
from security import (
    generate_auth_token,
    ALLOWED_TEMPLATES,
    ALLOWED_THEMES,
    ALLOWED_ACCENTS,
    ALLOWED_SECTIONS,
    ALLOWED_STATUSES
)
from repositories.user_repository import UserRepository
from repositories.student_repository import StudentRepository
from repositories.project_repository import ProjectRepository
from repositories.portfolio_repository import PortfolioRepository
from portfolio_generator import PortfolioGenerator
from resume_data import ResumeData, ProjectData


STYLE_CSS_HASH = "d35e4369f7bc08f4882ce3a1104a56acecb2c5a53a876ec5180ead0aae635b59"
INDEX_HTML_HASH = "64accd6f43db002f4ebb44df770b251e307805563dc9aec291d2dd5296a9695c"
MAIN_JS_HASH = "4510814bb6e201abc018445c15f633870c80a163e8134e159de78bbfa2cda8bc"


def _compute_file_hash(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def get_db():
    return psycopg2.connect(**Config.get_db_params())


@pytest.fixture
def client():
    main.app.config["TESTING"] = True
    with main.app.test_client() as client:
        yield client


@pytest.fixture
def user_a():
    """Create a unique test user A and associated student record."""
    uid = uuid.uuid4().hex[:8]
    email = f"user_a_{uid}@test.com"
    u_repo = UserRepository(get_db)
    user = u_repo.create_user(email, "Password123!")
    token = generate_auth_token(user["id"], user["email"])

    # Create associated student record
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO students (
            name, email, bio, skills, education, experience, achievements,
            parser_used, headline, ai_provider, resume_hash, processing_status,
            resume_filename, resume_text, user_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s
        ) RETURNING id
        """,
        (
            f"User A {uid}", email, "Original Bio for User A", "Python, Flask, SQL",
            "B.Tech Computer Science", "Intern at TechCorp", "First place hackathon",
            "pdfplumber", "Full Stack Developer", "Local Intelligence",
            hashlib.sha256(b"User A resume text").hexdigest(), "completed",
            "resume_a.pdf", "Original resume text for User A", user["id"]
        )
    )
    student_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return {
        "user_id": user["id"],
        "email": email,
        "student_id": student_id,
        "token": token,
        "auth_header": {"Authorization": f"Bearer {token}"}
    }


@pytest.fixture
def user_b():
    """Create a unique test user B and associated student record."""
    uid = uuid.uuid4().hex[:8]
    email = f"user_b_{uid}@test.com"
    u_repo = UserRepository(get_db)
    user = u_repo.create_user(email, "Password123!")
    token = generate_auth_token(user["id"], user["email"])

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO students (
            name, email, bio, skills, education, experience, achievements,
            parser_used, headline, ai_provider, resume_hash, processing_status,
            resume_filename, resume_text, user_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s
        ) RETURNING id
        """,
        (
            f"User B {uid}", email, "Original Bio for User B", "React, TypeScript",
            "BCA", "Frontend Dev at Startup", "Winner Open Source Award",
            "pypdf", "Frontend Engineer", "Local Intelligence",
            hashlib.sha256(b"User B resume text").hexdigest(), "completed",
            "resume_b.pdf", "Original resume text for User B", user["id"]
        )
    )
    student_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return {
        "user_id": user["id"],
        "email": email,
        "student_id": student_id,
        "token": token,
        "auth_header": {"Authorization": f"Bearer {token}"}
    }


# ============================================================
# 1. USER PROFILE ENDPOINT (/api/v1/me)
# ============================================================

def test_api_v1_me_authenticated(client, user_a):
    """GET /api/v1/me returns user profile and student ID when authenticated."""
    resp = client.get("/api/v1/me", headers=user_a["auth_header"])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["data"]["user_id"] == user_a["user_id"]
    assert data["data"]["email"] == user_a["email"]
    assert data["data"]["student_id"] == user_a["student_id"]


def test_api_v1_me_unauthenticated(client):
    """GET /api/v1/me rejects unauthenticated request with 401."""
    resp = client.get("/api/v1/me")
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"


# ============================================================
# 2. RESUME MANAGEMENT ENDPOINTS (/api/v1/resume)
# ============================================================

def test_api_v1_resume_metadata_omits_raw_text_by_default(client, user_a):
    """GET /api/v1/resume returns metadata but omits raw text by default."""
    resp = client.get("/api/v1/resume", headers=user_a["auth_header"])
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["student_id"] == user_a["student_id"]
    assert data["resume_filename"] == "resume_a.pdf"
    assert data["parser_used"] == "pdfplumber"
    assert data["ai_provider"] == "Local Intelligence"
    assert data["has_resume"] is True
    assert "resume_text" not in data


def test_api_v1_resume_metadata_includes_raw_text_when_requested(client, user_a):
    """GET /api/v1/resume?include_text=true returns raw resume text."""
    resp = client.get("/api/v1/resume?include_text=true", headers=user_a["auth_header"])
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert "resume_text" in data
    assert "Original resume text for User A" in data["resume_text"]


def test_api_v1_delete_resume_clears_file_and_preserves_student(client, user_a):
    """DELETE /api/v1/resume clears resume info while preserving student profile."""
    del_resp = client.delete("/api/v1/resume", headers=user_a["auth_header"])
    assert del_resp.status_code == 200
    assert del_resp.get_json()["success"] is True

    # Check student record in DB
    s_repo = StudentRepository(get_db)
    student = s_repo.get_student_by_id(user_a["student_id"])
    assert student is not None
    assert student["name"].startswith("User A")
    assert student["resume_filename"] is None
    assert student["processing_status"] == "pending"

    # Check GET /api/v1/resume reflects cleared state
    get_resp = client.get("/api/v1/resume", headers=user_a["auth_header"])
    assert get_resp.status_code == 200
    data = get_resp.get_json()["data"]
    assert data["resume_filename"] is None
    assert data["processing_status"] == "pending"


# ============================================================
# 3. PROJECT CRUD ENDPOINTS (/api/v1/projects)
# ============================================================

def test_api_v1_projects_crud_lifecycle(client, user_a):
    """Full lifecycle: create project, list projects, update project, delete project."""
    # 1. Create project
    create_payload = {
        "title": "Cloud Dashboard",
        "description": "Real-time analytics dashboard with React and Flask",
        "technologies": ["React", "Flask", "PostgreSQL"],
        "github_url": "https://github.com/usera/dashboard",
        "live_url": "https://dashboard.usera.dev",
        "category": "Web Development"
    }
    post_resp = client.post("/api/v1/projects", headers=user_a["auth_header"], json=create_payload)
    assert post_resp.status_code == 201
    created_proj = post_resp.get_json()["data"]
    assert created_proj["title"] == "Cloud Dashboard"
    assert created_proj["student_id"] == user_a["student_id"]
    proj_id = created_proj["id"]

    # 2. List projects
    list_resp = client.get("/api/v1/projects", headers=user_a["auth_header"])
    assert list_resp.status_code == 200
    projs = list_resp.get_json()["data"]
    assert any(p["id"] == proj_id for p in projs)

    # 3. Update project
    update_payload = {
        "title": "Cloud Dashboard 2.0",
        "technologies": ["React", "Flask", "PostgreSQL", "Docker"]
    }
    put_resp = client.put(f"/api/v1/projects/{proj_id}", headers=user_a["auth_header"], json=update_payload)
    assert put_resp.status_code == 200
    updated_proj = put_resp.get_json()["data"]
    assert updated_proj["title"] == "Cloud Dashboard 2.0"
    assert "Docker" in updated_proj["technologies"]

    # 4. Delete project
    del_resp = client.delete(f"/api/v1/projects/{proj_id}", headers=user_a["auth_header"])
    assert del_resp.status_code == 200
    assert del_resp.get_json()["data"]["deleted"] is True

    # 5. Verify deleted from list
    list_resp2 = client.get("/api/v1/projects", headers=user_a["auth_header"])
    projs2 = list_resp2.get_json()["data"]
    assert not any(p["id"] == proj_id for p in projs2)


def test_api_v1_projects_validation_checks(client, user_a):
    """Validation: project title required, dangerous URL rejected."""
    # Missing title
    resp1 = client.post("/api/v1/projects", headers=user_a["auth_header"], json={"description": "No title"})
    assert resp1.status_code == 400
    assert resp1.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Dangerous javascript: scheme in github_url
    resp2 = client.post("/api/v1/projects", headers=user_a["auth_header"], json={
        "title": "Malicious Project",
        "github_url": "javascript:alert(1)"
    })
    assert resp2.status_code == 400
    assert resp2.get_json()["error"]["code"] == "VALIDATION_ERROR"


# ============================================================
# 4. PROJECT OWNERSHIP & ISOLATION
# ============================================================

def test_api_v1_project_ownership_isolation(client, user_a, user_b):
    """User B cannot modify or delete User A's project (returns 403)."""
    # User A creates a project
    post_resp = client.post("/api/v1/projects", headers=user_a["auth_header"], json={
        "title": "Private Project of User A",
        "description": "Secret stuff"
    })
    assert post_resp.status_code == 201
    proj_id = post_resp.get_json()["data"]["id"]

    # User B attempts to update User A's project -> 403
    put_resp = client.put(f"/api/v1/projects/{proj_id}", headers=user_b["auth_header"], json={
        "title": "Hacked Title"
    })
    assert put_resp.status_code == 403
    assert put_resp.get_json()["error"]["code"] == "FORBIDDEN"

    # User B attempts to delete User A's project -> 403
    del_resp = client.delete(f"/api/v1/projects/{proj_id}", headers=user_b["auth_header"])
    assert del_resp.status_code == 403
    assert del_resp.get_json()["error"]["code"] == "FORBIDDEN"

    # Unauthenticated user attempts update -> 401
    anon_put = client.put(f"/api/v1/projects/{proj_id}", json={"title": "Anon edit"})
    assert anon_put.status_code == 401

    # Project should still exist untouched
    p_repo = ProjectRepository(get_db)
    proj = p_repo.get_project_by_id(proj_id)
    assert proj is not None
    assert proj["title"] == "Private Project of User A"


# ============================================================
# 5. PORTFOLIO CUSTOMIZATION VALIDATION (PUT /api/v1/portfolio)
# ============================================================

def test_api_v1_portfolio_customization_validation(client, user_a):
    """Validate template, theme, accent, status, section_visibility, social_links."""
    # Invalid template
    r1 = client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={"template": "neon_cyber"})
    assert r1.status_code == 400
    assert r1.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Invalid theme
    r2 = client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={"theme": "solarized"})
    assert r2.status_code == 400
    assert r2.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Invalid accent
    r3 = client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={"accent": "hotpink"})
    assert r3.status_code == 400
    assert r3.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Invalid status
    r4 = client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={"status": "archived"})
    assert r4.status_code == 400
    assert r4.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Invalid section name in section_visibility
    r5 = client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={
        "section_visibility": {"secret_section": True}
    })
    assert r5.status_code == 400
    assert r5.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Dangerous social link
    r6 = client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={
        "social_links": {"github": "javascript:evil()"}
    })
    assert r6.status_code == 400
    assert r6.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # Custom name too long (> 100 chars)
    r7 = client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={
        "custom_name": "A" * 150
    })
    assert r7.status_code == 400
    assert r7.get_json()["error"]["code"] == "VALIDATION_ERROR"


# ============================================================
# 6. FAST SETTINGS UPDATE WITHOUT AI RERUN
# ============================================================

def test_api_v1_portfolio_fast_settings_update_no_ai_rerun(client, user_a):
    """Updating settings is a fast DB update that does NOT re-run AI or change parser metadata."""
    # Capture initial student metadata
    s_repo = StudentRepository(get_db)
    init_student = s_repo.get_student_by_id(user_a["student_id"])
    init_provider = init_student["ai_provider"]
    init_parser = init_student["parser_used"]
    init_hash = init_student["resume_hash"]

    # Perform valid settings update
    settings_payload = {
        "template": "modern",
        "theme": "dark",
        "accent": "purple",
        "status": "published",
        "custom_name": "Alex Apex Sharma",
        "custom_headline": "Senior Full-Stack Architect",
        "custom_bio": "Passionate cloud software engineer building resilient web platforms.",
        "section_visibility": {
            "about": True,
            "skills": True,
            "education": True,
            "experience": False,
            "projects": True,
            "achievements": False
        },
        "social_links": {
            "github": "https://github.com/alexsharma",
            "linkedin": "https://linkedin.com/in/alexsharma"
        }
    }

    put_resp = client.put("/api/v1/portfolio", headers=user_a["auth_header"], json=settings_payload)
    assert put_resp.status_code == 200
    res_data = put_resp.get_json()["data"]
    assert res_data["template"] == "modern"
    assert res_data["theme"] == "dark"
    assert res_data["accent"] == "purple"
    assert res_data["custom_name"] == "Alex Apex Sharma"

    # Verify student AI provider, parser, and resume_hash are UNCHANGED
    post_student = s_repo.get_student_by_id(user_a["student_id"])
    assert post_student["ai_provider"] == init_provider
    assert post_student["parser_used"] == init_parser
    assert post_student["resume_hash"] == init_hash


# ============================================================
# 7. WORKSPACE PORTFOLIO & CUSTOMIZATION OVERLAY
# ============================================================

def test_api_v1_portfolio_me_and_preview_overlay(client, user_a):
    """GET /api/v1/portfolio/me and preview reflect custom fields and settings."""
    # Set custom headline & bio
    client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={
        "custom_name": "Custom User A",
        "custom_headline": "AI Solutions Engineer",
        "accent": "cyan"
    })

    # GET /api/v1/portfolio/me
    resp = client.get("/api/v1/portfolio/me", headers=user_a["auth_header"])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["profile"]["name"] == "Custom User A"
    assert data["profile"]["headline"] == "AI Solutions Engineer"
    assert data["customization"]["accent"] == "cyan"

    # GET /api/v1/portfolio/me/preview
    prev_resp = client.get("/api/v1/portfolio/me/preview", headers=user_a["auth_header"])
    assert prev_resp.status_code == 200
    prev_data = prev_resp.get_json()
    assert prev_data["is_preview"] is True
    assert prev_data["profile"]["name"] == "Custom User A"


# ============================================================
# 8. DRAFT MODE VS PUBLISHED VISIBILITY
# ============================================================

def test_draft_mode_hides_portfolio_from_public_and_other_users(client, user_a, user_b):
    """Draft portfolio returns 403 to public & other users, but 200 to owner."""
    # Set User A's portfolio to draft
    client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={"status": "draft"})

    # 1. Unauthenticated visitor tries to view User A's portfolio -> 403
    pub_resp = client.get(f"/api/v1/portfolio/{user_a['student_id']}")
    assert pub_resp.status_code == 403

    # 2. User B tries to view User A's draft portfolio -> 403
    other_resp = client.get(f"/api/v1/portfolio/{user_a['student_id']}", headers=user_b["auth_header"])
    assert other_resp.status_code == 403

    # 3. User A (owner) views portfolio via /api/v1/portfolio/<id> -> 200
    owner_resp = client.get(f"/api/v1/portfolio/{user_a['student_id']}", headers=user_a["auth_header"])
    assert owner_resp.status_code == 200
    owner_data = owner_resp.get_json().get("data", owner_resp.get_json())
    assert owner_data["is_draft"] is True
    assert owner_data["status"] == "draft"

    # 4. User A sets status back to published
    client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={"status": "published"})

    # 5. Unauthenticated visitor can now view User A's portfolio -> 200
    pub_resp2 = client.get(f"/api/v1/portfolio/{user_a['student_id']}")
    assert pub_resp2.status_code == 200
    pub_data = pub_resp2.get_json().get("data", pub_resp2.get_json())
    assert pub_data["status"] == "published"


# ============================================================
# 9. PROJECT ORDERING IN PORTFOLIO
# ============================================================

def test_portfolio_project_order_customization(client, user_a):
    """Projects in portfolio are ordered according to configured project_order."""
    # Create two projects
    p1 = client.post("/api/v1/projects", headers=user_a["auth_header"], json={"title": "Project Alpha"}).get_json()["data"]
    p2 = client.post("/api/v1/projects", headers=user_a["auth_header"], json={"title": "Project Beta"}).get_json()["data"]

    # Set reverse order: [p2['id'], p1['id']]
    client.put("/api/v1/portfolio", headers=user_a["auth_header"], json={
        "project_order": [p2["id"], p1["id"]]
    })

    # Fetch projects via /api/v1/projects
    list_resp = client.get("/api/v1/projects", headers=user_a["auth_header"])
    ordered_ids = [p["id"] for p in list_resp.get_json()["data"]]
    # p2 should appear before p1
    assert ordered_ids.index(p2["id"]) < ordered_ids.index(p1["id"])

    # Fetch portfolio via /api/v1/portfolio/me
    port_resp = client.get("/api/v1/portfolio/me", headers=user_a["auth_header"])
    port_projs = port_resp.get_json()["projects"]
    port_ids = [p["id"] for p in port_projs if "id" in p]
    assert port_ids.index(p2["id"]) < port_ids.index(p1["id"])


# ============================================================
# 10. FRONTEND DESIGN INTEGRITY (FROZEN)
# ============================================================

def test_frontend_frozen_design_sha256():
    """Verify static/css/style.css, index.html, and main.js are strictly preserved."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(base_dir, "static", "css", "style.css")
    html_path = os.path.join(base_dir, "templates", "index.html")
    js_path = os.path.join(base_dir, "static", "js", "main.js")

    assert _compute_file_hash(css_path) == STYLE_CSS_HASH, "CSS file was unexpectedly modified!"
    assert _compute_file_hash(html_path) == INDEX_HTML_HASH, "HTML template was unexpectedly modified!"
    assert _compute_file_hash(js_path) == MAIN_JS_HASH, "JS file was unexpectedly modified!"


# ============================================================
# DIRECT EXECUTION SUPPORT
# ============================================================

if __name__ == "__main__":
    import sys
    print("=" * 60)
    print("RUNNING PHASE 5 TEST SUITE DIRECTLY")
    print("=" * 60)
    code = pytest.main(["-v", __file__])
    sys.exit(code)
