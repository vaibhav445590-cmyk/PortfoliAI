"""
PortfoliAI — Phase 6 Premium Cinematic UI / UX Transformation Test Suite
Automated pytest-compatible verification of:
    1. Static Asset Integrity (cinematic.css, workspace.css, templates.css, app.js, workspace.js, preview.js, app.html)
    2. Home Route (GET /) serves cinematic landing page
    3. Legacy Mode (GET /?legacy=1) backward compatibility with index.html
    4. Authenticated Workspace Route (GET /workspace)
    5. Public Portfolio Route (GET /p/<student_id>) with 5 Archetypes (Glass, Minimal, Modern, Developer, Dark)
    6. Draft Mode Protection on /p/<student_id> (403 for anonymous/other users, 200 for owner)
    7. Project Drag-and-Drop Order Persistence via PUT /api/v1/portfolio and rendering in /p/<student_id>
    8. Custom Field Overlays (custom_name, custom_headline, custom_bio, social_links) on /p/<student_id>
    9. Section Visibility Controls (toggling sections off/on) on /p/<student_id>
"""

import os
import uuid
import hashlib
import pytest
import psycopg2

from config import Config
import main
from security import generate_auth_token
from repositories.user_repository import UserRepository
from repositories.student_repository import StudentRepository
from repositories.project_repository import ProjectRepository
from repositories.portfolio_repository import PortfolioRepository


def get_db():
    return psycopg2.connect(**Config.get_db_params())


@pytest.fixture
def client():
    main.app.config["TESTING"] = True
    with main.app.test_client() as client:
        yield client


@pytest.fixture
def user_alpha():
    """Create a unique test user Alpha and associated student record."""
    uid = uuid.uuid4().hex[:8]
    email = f"alpha_{uid}@test.com"
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
            f"Alpha Student {uid}", email, "Original Bio for Alpha", "Python, Flask, Docker, PostgreSQL",
            "B.Tech Computer Science", "SWE Intern at ScaleCorp", "First Prize AI Hackathon",
            "pdfplumber", "Full-Stack AI Engineer", "Local Intelligence",
            hashlib.sha256(b"Alpha resume text").hexdigest(), "completed",
            "resume_alpha.pdf", "Original resume text for Alpha", user["id"]
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
def user_beta():
    """Create a unique test user Beta."""
    uid = uuid.uuid4().hex[:8]
    email = f"beta_{uid}@test.com"
    u_repo = UserRepository(get_db)
    user = u_repo.create_user(email, "Password123!")
    token = generate_auth_token(user["id"], user["email"])

    return {
        "user_id": user["id"],
        "email": email,
        "token": token,
        "auth_header": {"Authorization": f"Bearer {token}"}
    }


# ============================================================
# 1. STATIC ASSET INTEGRITY
# ============================================================

def test_phase6_static_assets_exist_and_non_empty():
    """Verify all required Phase 6 CSS, JS, and HTML template files exist with substantive code."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    required_files = [
        os.path.join(base_dir, "static", "css", "cinematic.css"),
        os.path.join(base_dir, "static", "css", "workspace.css"),
        os.path.join(base_dir, "static", "css", "templates.css"),
        os.path.join(base_dir, "static", "js", "app.js"),
        os.path.join(base_dir, "static", "js", "workspace.js"),
        os.path.join(base_dir, "static", "js", "preview.js"),
        os.path.join(base_dir, "templates", "app.html"),
    ]

    for fpath in required_files:
        assert os.path.exists(fpath), f"Missing required Phase 6 file: {fpath}"
        assert os.path.getsize(fpath) > 500, f"File {fpath} is suspiciously small ({os.path.getsize(fpath)} bytes)"


# ============================================================
# 2. HOME ROUTE (GET /)
# ============================================================

def test_home_route_renders_cinematic_landing(client):
    """GET / returns 200 and contains Phase 6 cinematic elements."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "PortfoliAI" in html
    assert "hero3DResume" in html
    assert "cinematic.css" in html
    assert "workspace.css" in html
    assert "templates.css" in html


def test_home_route_legacy_mode(client):
    """GET /?legacy=1 returns 200 and renders original index.html."""
    resp = client.get("/?legacy=1")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "style.css" in html
    assert "main.js" in html


# ============================================================
# 3. WORKSPACE ROUTE (GET /workspace)
# ============================================================

def test_workspace_route_renders_workspace_view(client):
    """GET /workspace returns 200 with workspace sections."""
    resp = client.get("/workspace")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "STUDENT WORKSPACE" in html
    assert "viewOverview" in html
    assert "viewResume" in html
    assert "viewProjects" in html
    assert "viewStudio" in html
    assert "viewPreview" in html


# ============================================================
# 4. PUBLIC PORTFOLIO ARCHETYPES & THEMES (/p/<student_id>)
# ============================================================

@pytest.mark.parametrize("template_name", ["glass", "minimal", "modern", "developer", "dark"])
def test_public_portfolio_renders_all_templates(client, user_alpha, template_name):
    """Verify /p/<id> renders all 5 template archetypes correctly."""
    # Configure template and publish
    p_repo = PortfolioRepository(get_db)
    p_repo.save_portfolio_settings(user_alpha["student_id"], {
        "template": template_name,
        "theme": "dark" if template_name == "dark" else "glass",
        "accent": "emerald",
        "status": "published"
    })

    resp = client.get(f"/p/{user_alpha['student_id']}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert f"template-{template_name}" in html
    assert "accent-emerald" in html
    assert "Alpha Student" in html


# ============================================================
# 5. DRAFT PROTECTION ON /p/<student_id>
# ============================================================

def test_public_portfolio_draft_mode_enforcement(client, user_alpha, user_beta):
    """Draft status on /p/<student_id> blocks visitors with 403, allows owner with 200."""
    p_repo = PortfolioRepository(get_db)
    p_repo.save_portfolio_settings(user_alpha["student_id"], {"status": "draft"})

    # 1. Anonymous visitor -> 403
    r_anon = client.get(f"/p/{user_alpha['student_id']}")
    assert r_anon.status_code == 403
    assert b"draft mode" in r_anon.data

    # 2. Other user -> 403
    r_other = client.get(f"/p/{user_alpha['student_id']}", headers=user_beta["auth_header"])
    assert r_other.status_code == 403
    assert b"draft mode" in r_other.data

    # 3. Owner -> 200
    r_owner = client.get(f"/p/{user_alpha['student_id']}", headers=user_alpha["auth_header"])
    assert r_owner.status_code == 200
    assert b"Alpha Student" in r_owner.data


# ============================================================
# 6. PROJECT REORDERING & PERSISTENCE
# ============================================================

def test_project_reordering_and_public_reflection(client, user_alpha):
    """Projects reordered via PUT /api/v1/portfolio reflect correctly in /p/<student_id>."""
    p_repo = ProjectRepository(get_db)
    p1 = p_repo.create_project(user_alpha["student_id"], {"title": "First Project Alpha", "technologies": ["Python"]})
    p2 = p_repo.create_project(user_alpha["student_id"], {"title": "Second Project Beta", "technologies": ["React"]})

    # Set status to published and reverse project order
    client.put("/api/v1/portfolio", headers=user_alpha["auth_header"], json={
        "status": "published",
        "project_order": [p2["id"], p1["id"]]
    })

    # Fetch public portfolio HTML
    resp = client.get(f"/p/{user_alpha['student_id']}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    idx_p1 = html.find("First Project Alpha")
    idx_p2 = html.find("Second Project Beta")
    assert idx_p1 != -1 and idx_p2 != -1
    # p2 must appear before p1 in the rendered HTML
    assert idx_p2 < idx_p1


# ============================================================
# 7. CUSTOM FIELD OVERLAYS ON PUBLIC PORTFOLIO
# ============================================================

def test_custom_field_overlays_on_public_portfolio(client, user_alpha):
    """custom_name, custom_headline, custom_bio, and social_links overlay correctly."""
    client.put("/api/v1/portfolio", headers=user_alpha["auth_header"], json={
        "status": "published",
        "custom_name": "Overridden Alpha Persona",
        "custom_headline": "Principal Quantum Systems Architect",
        "custom_bio": "Crafting resilient cloud-native computing architectures.",
        "social_links": {
            "github": "https://github.com/alphadev",
            "linkedin": "https://linkedin.com/in/alphadev"
        }
    })

    resp = client.get(f"/p/{user_alpha['student_id']}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Overridden Alpha Persona" in html
    assert "Principal Quantum Systems Architect" in html
    assert "Crafting resilient cloud-native computing architectures." in html
    assert "https://github.com/alphadev" in html
    assert "https://linkedin.com/in/alphadev" in html


# ============================================================
# 8. SECTION VISIBILITY TOGGLES
# ============================================================

def test_section_visibility_toggles(client, user_alpha):
    """Disabled sections are completely excluded from rendered /p/<student_id> HTML."""
    # Disable experience and achievements
    client.put("/api/v1/portfolio", headers=user_alpha["auth_header"], json={
        "status": "published",
        "section_visibility": {
            "about": True,
            "skills": True,
            "projects": True,
            "education": True,
            "experience": False,
            "achievements": False
        }
    })

    resp = client.get(f"/p/{user_alpha['student_id']}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    # SWE Intern at ScaleCorp (experience) and First Prize AI Hackathon (achievements) should NOT be present
    assert "SWE Intern at ScaleCorp" not in html
    assert "First Prize AI Hackathon" not in html
    # But skills should still be present
    assert "Python" in html


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", __file__]))
