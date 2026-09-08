"""
PortfoliAI — Phase 4.1 Authentication & Authorization Hardening Test Suite
Pytest-compatible verification of:
    1. JWT token generation, issuance, and cryptographic validation
    2. Authentication endpoints (/api/v1/auth/register, /api/v1/auth/login)
    3. Token error handling (expired, malformed, invalid signature, missing)
    4. Student ownership matrix on mutating endpoints:
       - POST /api/v1/resume/upload
       - POST /generate-portfolio
       - POST /upload-resume
       - POST /api/enrich-resume
       Rules:
         User A -> Student A: ALLOWED (200 / 201)
         User A -> Student B: FORBIDDEN (403)
         User B -> Student B: ALLOWED (200 / 201)
         User B -> Student A: FORBIDDEN (403)
         No Auth -> Student A: UNAUTHORIZED (401)
         No Auth -> Student B: UNAUTHORIZED (401)
    5. Backward compatibility for legacy unowned records (user_id IS NULL)
    6. Public portfolio read data protection (no leaked secrets, passwords, or raw resume_text)
    7. Clean configuration: no hardcoded database passwords
    8. Frontend SHA-256 integrity verification
"""

import os
import io
import json
import uuid
import hashlib
import psycopg2
import pytest

from config import Config
import main
from security import (
    generate_auth_token,
    decode_auth_token,
    check_student_ownership,
    get_current_user_from_request
)
from repositories.user_repository import UserRepository
from repositories.student_repository import StudentRepository


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


def create_minimal_pdf_bytes(text: str = "Test User\nSoftware Engineer\nPython Flask SQL\nEducation: BS CS\nProjects: App") -> bytes:
    """Generate a valid minimal single-page PDF containing text for upload tests."""
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream_content = f"BT /F1 12 Tf 72 712 Td ({escaped_text}) Tj ET"
    stream_length = len(stream_content.encode("latin-1"))

    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"5 0 obj << /Length " + str(stream_length).encode("ascii") + b" >>\nstream\n"
        + stream_content.encode("latin-1") + b"\nendstream\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"0000000266 00000 n \n0000000340 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n450\n%%EOF\n"
    )
    return pdf


# ============================================================
# 1. JWT TOKEN GENERATION & DECODING TESTS
# ============================================================

def test_jwt_token_generation_and_decoding():
    """Verify JWT Bearer tokens are properly signed, structured, and decoded."""
    user_id = 12345
    email = "testjwt@example.com"
    token = generate_auth_token(user_id=user_id, email=email, expires_in_seconds=3600)
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    is_valid, payload, err = decode_auth_token(token)
    assert is_valid is True
    assert err is None
    assert payload["user_id"] == user_id
    assert payload["email"] == email
    assert payload["sub"] == str(user_id)
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_token_expiration_and_invalidity():
    """Verify expired and forged tokens are rejected."""
    # Expired token
    expired_token = generate_auth_token(user_id=999, email="exp@example.com", expires_in_seconds=-10)
    is_valid, payload, err = decode_auth_token(expired_token)
    assert is_valid is False
    assert payload is None
    assert "expired" in err.lower()

    # Tampered / invalid token
    tampered_token = expired_token[:-4] + "xyz1"
    is_valid, payload, err = decode_auth_token(tampered_token)
    assert is_valid is False
    assert payload is None

    # Empty token
    is_valid, payload, err = decode_auth_token("")
    assert is_valid is False


# ============================================================
# 2. AUTHENTICATION API ENDPOINTS WITH JWT
# ============================================================

def test_auth_register_returns_jwt():
    """POST /api/v1/auth/register must issue a valid JWT token."""
    client = main.app.test_client()
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/v1/auth/register", json={
        "email": unique_email,
        "password": "SecurePassword123!"
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["success"] is True
    assert "data" in body
    assert "token" in body["data"]
    token = body["data"]["token"]
    assert body["data"]["email"] == unique_email

    is_valid, payload, err = decode_auth_token(token)
    assert is_valid is True
    assert payload["email"] == unique_email


def test_auth_login_returns_jwt():
    """POST /api/v1/auth/login must issue a valid JWT token."""
    client = main.app.test_client()
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "MySecretPassword456!"

    # Register first
    client.post("/api/v1/auth/register", json={"email": unique_email, "password": pwd})

    # Login
    resp = client.post("/api/v1/auth/login", json={"email": unique_email, "password": pwd})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert "token" in body["data"]
    token = body["data"]["token"]

    is_valid, payload, err = decode_auth_token(token)
    assert is_valid is True
    assert payload["email"] == unique_email


def test_auth_login_invalid_credentials():
    """POST /api/v1/auth/login must return 401 on incorrect credentials without token."""
    client = main.app.test_client()
    resp = client.post("/api/v1/auth/login", json={"email": "nonexistent@example.com", "password": "wrong"})
    assert resp.status_code == 401
    body = resp.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


# ============================================================
# 3. OWNERSHIP MATRIX ON MUTATING ENDPOINTS
# ============================================================

def _setup_two_users_and_students():
    """Helper to create User A & Student A, User B & Student B."""
    client = main.app.test_client()
    email_a = f"usera_{uuid.uuid4().hex[:8]}@example.com"
    email_b = f"userb_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SharedPassword123!"

    resp_a = client.post("/api/v1/auth/register", json={"email": email_a, "password": pwd})
    token_a = resp_a.get_json()["data"]["token"]
    user_a_id = resp_a.get_json()["data"]["user_id"]

    resp_b = client.post("/api/v1/auth/register", json={"email": email_b, "password": pwd})
    token_b = resp_b.get_json()["data"]["token"]
    user_b_id = resp_b.get_json()["data"]["user_id"]

    # Create Student A owned by User A
    pdf_a = create_minimal_pdf_bytes(f"Student Alpha\nEmail: {email_a}\nFull Stack Developer\nPython Django React\nEducation: MIT\nProjects: Portal")
    upload_resp_a = client.post(
        "/api/v1/resume/upload",
        data={"resume": (io.BytesIO(pdf_a), "resume_a.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert upload_resp_a.status_code == 201
    student_a_id = upload_resp_a.get_json()["data"]["student_id"]

    # Create Student B owned by User B
    pdf_b = create_minimal_pdf_bytes(f"Student Beta\nEmail: {email_b}\nData Scientist\nPython PyTorch SQL\nEducation: Stanford\nProjects: ML Model")
    upload_resp_b = client.post(
        "/api/v1/resume/upload",
        data={"resume": (io.BytesIO(pdf_b), "resume_b.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert upload_resp_b.status_code == 201
    student_b_id = upload_resp_b.get_json()["data"]["student_id"]

    return {
        "client": client,
        "user_a": {"id": user_a_id, "token": token_a, "student_id": student_a_id, "email": email_a},
        "user_b": {"id": user_b_id, "token": token_b, "student_id": student_b_id, "email": email_b}
    }


def test_ownership_matrix_resume_upload():
    """Verify ownership enforcement on POST /api/v1/resume/upload."""
    env = _setup_two_users_and_students()
    client = env["client"]
    user_a = env["user_a"]
    user_b = env["user_b"]
    pdf_update_a = create_minimal_pdf_bytes(f"Updated Resume A\nEmail: {user_a['email']}\nSenior Engineer\nPython Kubernetes")
    pdf_update_b = create_minimal_pdf_bytes(f"Updated Resume B\nEmail: {user_b['email']}\nSenior Engineer\nPython Kubernetes")

    # 1. User A -> Student A: ALLOWED (201)
    res = client.post(
        f"/api/v1/resume/upload?student_id={user_a['student_id']}",
        data={"resume": (io.BytesIO(pdf_update_a), "update_a.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {user_a['token']}"}
    )
    assert res.status_code == 201

    # 2. User A -> Student B: FORBIDDEN (403)
    res = client.post(
        f"/api/v1/resume/upload?student_id={user_b['student_id']}",
        data={"resume": (io.BytesIO(pdf_update_a), "hack_b.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {user_a['token']}"}
    )
    assert res.status_code == 403
    assert res.get_json()["error"]["code"] == "FORBIDDEN"

    # 3. User B -> Student B: ALLOWED (201)
    res = client.post(
        f"/api/v1/resume/upload?student_id={user_b['student_id']}",
        data={"resume": (io.BytesIO(pdf_update_b), "update_b.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {user_b['token']}"}
    )
    assert res.status_code == 201

    # 4. User B -> Student A: FORBIDDEN (403)
    res = client.post(
        f"/api/v1/resume/upload?student_id={user_a['student_id']}",
        data={"resume": (io.BytesIO(pdf_update_b), "hack_a.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {user_b['token']}"}
    )
    assert res.status_code == 403
    assert res.get_json()["error"]["code"] == "FORBIDDEN"

    # 5. No Auth -> Student A: UNAUTHORIZED (401)
    res = client.post(
        f"/api/v1/resume/upload?student_id={user_a['student_id']}",
        data={"resume": (io.BytesIO(pdf_update_a), "no_auth.pdf")},
        content_type="multipart/form-data"
    )
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "UNAUTHORIZED"

    # 6. No Auth -> Student B: UNAUTHORIZED (401)
    res = client.post(
        f"/api/v1/resume/upload?student_id={user_b['student_id']}",
        data={"resume": (io.BytesIO(pdf_update_b), "no_auth.pdf")},
        content_type="multipart/form-data"
    )
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_ownership_matrix_generate_portfolio():
    """Verify ownership enforcement on POST /generate-portfolio."""
    env = _setup_two_users_and_students()
    client = env["client"]
    user_a = env["user_a"]
    user_b = env["user_b"]

    # 1. User A -> Student A: ALLOWED (200)
    res = client.post(
        "/generate-portfolio",
        json={"student_id": user_a["student_id"]},
        headers={"Authorization": f"Bearer {user_a['token']}"}
    )
    assert res.status_code == 200

    # 2. User A -> Student B: FORBIDDEN (403)
    res = client.post(
        "/generate-portfolio",
        json={"student_id": user_b["student_id"]},
        headers={"Authorization": f"Bearer {user_a['token']}"}
    )
    assert res.status_code == 403

    # 3. User B -> Student B: ALLOWED (200)
    res = client.post(
        "/generate-portfolio",
        json={"student_id": user_b["student_id"]},
        headers={"Authorization": f"Bearer {user_b['token']}"}
    )
    assert res.status_code == 200

    # 4. User B -> Student A: FORBIDDEN (403)
    res = client.post(
        "/generate-portfolio",
        json={"student_id": user_a["student_id"]},
        headers={"Authorization": f"Bearer {user_b['token']}"}
    )
    assert res.status_code == 403

    # 5. No Auth -> Student A: UNAUTHORIZED (401)
    res = client.post(
        "/generate-portfolio",
        json={"student_id": user_a["student_id"]}
    )
    assert res.status_code == 401

    # 6. No Auth -> Student B: UNAUTHORIZED (401)
    res = client.post(
        "/generate-portfolio",
        json={"student_id": user_b["student_id"]}
    )
    assert res.status_code == 401


def test_ownership_matrix_legacy_upload_resume():
    """Verify ownership enforcement on legacy POST /upload-resume."""
    env = _setup_two_users_and_students()
    client = env["client"]
    user_a = env["user_a"]
    user_b = env["user_b"]
    pdf_bytes_a = create_minimal_pdf_bytes(f"Legacy Upload Test A\nEmail: {user_a['email']}\nPython Developer")
    pdf_bytes_b = create_minimal_pdf_bytes(f"Legacy Upload Test B\nEmail: {user_b['email']}\nPython Developer")

    # 1. User A -> Student A: ALLOWED (200)
    res = client.post(
        f"/upload-resume?student_id={user_a['student_id']}",
        data={"resume": (io.BytesIO(pdf_bytes_a), "legacy_a.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {user_a['token']}", "Accept": "application/json"}
    )
    assert res.status_code == 200

    # 2. User A -> Student B: FORBIDDEN (403)
    res = client.post(
        f"/upload-resume?student_id={user_b['student_id']}",
        data={"resume": (io.BytesIO(pdf_bytes_a), "legacy_b.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {user_a['token']}", "Accept": "application/json"}
    )
    assert res.status_code == 403

    # 3. User B -> Student B: ALLOWED (200)
    res = client.post(
        f"/upload-resume?student_id={user_b['student_id']}",
        data={"resume": (io.BytesIO(pdf_bytes_b), "legacy_b.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {user_b['token']}", "Accept": "application/json"}
    )
    assert res.status_code == 200

    # 4. User B -> Student A: FORBIDDEN (403)
    res = client.post(
        f"/upload-resume?student_id={user_a['student_id']}",
        data={"resume": (io.BytesIO(pdf_bytes_b), "legacy_a.pdf")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {user_b['token']}", "Accept": "application/json"}
    )
    assert res.status_code == 403

    # 5. No Auth -> Student A: UNAUTHORIZED (401)
    res = client.post(
        f"/upload-resume?student_id={user_a['student_id']}",
        data={"resume": (io.BytesIO(pdf_bytes_a), "legacy_noauth.pdf")},
        content_type="multipart/form-data",
        headers={"Accept": "application/json"}
    )
    assert res.status_code == 401


def test_ownership_matrix_enrich_resume():
    """Verify ownership enforcement on POST /api/enrich-resume."""
    env = _setup_two_users_and_students()
    client = env["client"]
    user_a = env["user_a"]
    user_b = env["user_b"]

    # 1. User A -> Student A: ALLOWED (200)
    res = client.post(
        "/api/enrich-resume",
        json={"student_id": user_a["student_id"]},
        headers={"Authorization": f"Bearer {user_a['token']}"}
    )
    assert res.status_code == 200

    # 2. User A -> Student B: FORBIDDEN (403)
    res = client.post(
        "/api/enrich-resume",
        json={"student_id": user_b["student_id"]},
        headers={"Authorization": f"Bearer {user_a['token']}"}
    )
    assert res.status_code == 403

    # 3. User B -> Student B: ALLOWED (200)
    res = client.post(
        "/api/enrich-resume",
        json={"student_id": user_b["student_id"]},
        headers={"Authorization": f"Bearer {user_b['token']}"}
    )
    assert res.status_code == 200

    # 4. User B -> Student A: FORBIDDEN (403)
    res = client.post(
        "/api/enrich-resume",
        json={"student_id": user_a["student_id"]},
        headers={"Authorization": f"Bearer {user_b['token']}"}
    )
    assert res.status_code == 403

    # 5. No Auth -> Student A: UNAUTHORIZED (401)
    res = client.post(
        "/api/enrich-resume",
        json={"student_id": user_a["student_id"]}
    )
    assert res.status_code == 401


# ============================================================
# 4. LEGACY UNOWNED RECORD COMPATIBILITY
# ============================================================

def test_legacy_unowned_record_compatibility():
    """Verify unowned records (user_id IS NULL) can still be generated and viewed."""
    conn = get_db()
    cursor = conn.cursor()
    legacy_email = f"legacy_{uuid.uuid4().hex[:8]}@example.com"
    cursor.execute(
        """
        INSERT INTO students (name, email, resume_text, processing_status, user_id)
        VALUES (%s, %s, %s, %s, NULL)
        RETURNING id
        """,
        ("Legacy Student", legacy_email, f"Legacy Student\nEmail: {legacy_email}\nSoftware Engineer\nPython SQL", "uploaded")
    )
    legacy_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    client = main.app.test_client()

    # Legacy generation without auth token is allowed for unowned records
    res = client.post("/generate-portfolio", json={"student_id": legacy_id})
    assert res.status_code == 200

    # Public portfolio read is allowed
    res = client.get(f"/api/v1/portfolio/{legacy_id}")
    assert res.status_code == 200
    assert res.get_json()["data"]["profile"]["name"] == "Legacy Student"


# ============================================================
# 5. PUBLIC PORTFOLIO LEAK PREVENTION
# ============================================================

def test_public_portfolio_does_not_leak_private_data():
    """Verify GET /api/v1/portfolio/<id> does NOT leak password_hash, raw resume_text, or secrets."""
    env = _setup_two_users_and_students()
    client = env["client"]
    student_a_id = env["user_a"]["student_id"]

    res = client.get(f"/api/v1/portfolio/{student_a_id}")
    assert res.status_code == 200
    data_str = json.dumps(res.get_json()).lower()

    # Must NOT leak confidential fields
    assert "password_hash" not in data_str
    assert "password" not in data_str
    assert "resume_text" not in data_str
    assert "token" not in data_str
    assert "jwt" not in data_str

    # Must contain public portfolio structure
    body = res.get_json()
    assert "profile" in body["data"]
    assert "stats" in body["data"]
    assert "skills" in body["data"]
    assert "projects" in body["data"]
    assert "metadata" in body["data"]


# ============================================================
# 6. CONFIGURATION & PASSWORD HARDENING
# ============================================================

def test_no_hardcoded_passwords_in_source():
    """Ensure no hardcoded fallback passwords exist in config or application files."""
    import inspect
    config_source = inspect.getsource(Config)
    # Ensure DB_PASSWORD defaults strictly to env var
    assert 'os.getenv("DB_PASSWORD", "")' in config_source or "os.getenv('DB_PASSWORD', '')" in config_source
    assert 'os.getenv("JWT_SECRET_KEY"' in config_source or "os.getenv('JWT_SECRET_KEY'" in config_source


# ============================================================
# 7. FRONTEND SHA-256 INTEGRITY
# ============================================================

def test_frontend_integrity_hashes():
    """Verify that CSS, HTML, and JS files have not been modified."""
    css_hash = _compute_file_hash(os.path.join("static", "css", "style.css"))
    assert css_hash == STYLE_CSS_HASH, f"CSS hash mismatch: expected {STYLE_CSS_HASH}, got {css_hash}"

    html_hash = _compute_file_hash(os.path.join("templates", "index.html"))
    assert html_hash == INDEX_HTML_HASH, f"HTML hash mismatch: expected {INDEX_HTML_HASH}, got {html_hash}"

    js_hash = _compute_file_hash(os.path.join("static", "js", "main.js"))
    assert js_hash == MAIN_JS_HASH, f"JS hash mismatch: expected {MAIN_JS_HASH}, got {js_hash}"


# ============================================================
# CLI RUNNER
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PortfoliAI — Phase 4.1 Test Suite")
    print("=" * 60)

    test_funcs = [
        ("JWT: Generation & Decoding", test_jwt_token_generation_and_decoding),
        ("JWT: Expiration & Tamper Rejection", test_jwt_token_expiration_and_invalidity),
        ("Auth API: Register Issues JWT", test_auth_register_returns_jwt),
        ("Auth API: Login Issues JWT", test_auth_login_returns_jwt),
        ("Auth API: Login Invalid Rejection", test_auth_login_invalid_credentials),
        ("Ownership: /api/v1/resume/upload Matrix", test_ownership_matrix_resume_upload),
        ("Ownership: /generate-portfolio Matrix", test_ownership_matrix_generate_portfolio),
        ("Ownership: /upload-resume Legacy Matrix", test_ownership_matrix_legacy_upload_resume),
        ("Ownership: /api/enrich-resume Matrix", test_ownership_matrix_enrich_resume),
        ("Backward Compatibility: Legacy Unowned Records", test_legacy_unowned_record_compatibility),
        ("Security: Public Portfolio Leak Prevention", test_public_portfolio_does_not_leak_private_data),
        ("Hardening: No Hardcoded DB Passwords", test_no_hardcoded_passwords_in_source),
        ("Frontend: SHA-256 Hashes Preserved", test_frontend_integrity_hashes),
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
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"Phase 4.1 Results: {passed}/{len(test_funcs)} PASSED")
    if failed > 0:
        print(f"FAILED: {failed} check(s)")
        raise SystemExit(1)
    else:
        print("All Phase 4.1 Authentication & Authorization tests PASSED!")
        print("=" * 60)
