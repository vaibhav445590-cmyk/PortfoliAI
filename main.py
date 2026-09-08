import os
import uuid
import json
import logging
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
from dotenv import load_dotenv

load_dotenv()

from werkzeug.utils import secure_filename
from pypdf import PdfReader
from config import Config
from parser_pipeline import create_default_pipeline
from ai.enrichment_service import create_default_enrichment_service, EnrichmentService
from portfolio_generator import PortfolioGenerator
from resume_data import ResumeData, ProjectData, CategorizedSkills
from resume_processor import (
    ResumeProcessor,
    validate_pdf_content,
    extract_pdf_text_from_bytes,
    extract_pdf_text_from_file,
    persist_student_data,
    persist_project_data
)
from repositories.user_repository import UserRepository
from repositories.student_repository import StudentRepository
from repositories.project_repository import ProjectRepository
from repositories.portfolio_repository import PortfolioRepository
from security import (
    rate_limit,
    sanitize_upload_filename,
    api_success,
    api_error,
    generate_auth_token,
    decode_auth_token,
    get_current_user_from_request,
    require_auth,
    check_student_ownership,
    check_project_ownership,
    validate_social_links,
    validate_section_visibility,
    validate_project_order,
    ALLOWED_TEMPLATES,
    ALLOWED_THEMES,
    ALLOWED_ACCENTS,
    ALLOWED_SECTIONS,
    ALLOWED_STATUSES,
    DANGEROUS_URL_SCHEMES,
    SAFE_URL_SCHEMES
)

# Setup structured logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("portfoliai")

app = Flask(__name__)

# ============================================================
# APP CONFIGURATION
# ============================================================

app.config["SECRET_KEY"] = Config.SECRET_KEY
app.config["UPLOAD_FOLDER"] = Config.UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH
ALLOWED_EXTENSIONS = Config.ALLOWED_EXTENSIONS

os.makedirs(
    Config.UPLOAD_FOLDER,
    exist_ok=True
)

# ============================================================
# PARSER PIPELINE, AI SERVICES & PROCESSOR
# ============================================================

resume_pipeline = create_default_pipeline()
enrichment_service = create_default_enrichment_service()
portfolio_generator = PortfolioGenerator()

# ============================================================
# DATABASE & REPOSITORIES
# ============================================================

def get_db_connection():
    return psycopg2.connect(**Config.get_db_params())

user_repo = UserRepository(get_db_connection)
student_repo = StudentRepository(get_db_connection)
project_repo = ProjectRepository(get_db_connection)
portfolio_repo = PortfolioRepository(get_db_connection)

resume_processor = ResumeProcessor(
    pipeline=resume_pipeline,
    enrichment_service=enrichment_service,
    portfolio_generator=portfolio_generator,
    db_connection_factory=get_db_connection
)


# ============================================================
# HELPERS
# ============================================================

def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


def extract_pdf_text(file_path):

    text, error = extract_pdf_text_from_file(file_path)
    return text


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()


        # ----------------------------------------------------
        # STUDENT
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                bio,
                skills,
                education,
                resume_filename,
                experience,
                achievements,
                parser_used,
                headline,
                categorized_skills,
                ai_provider
            FROM students
            ORDER BY id DESC
            LIMIT 1
            """
        )

        student_row = cursor.fetchone()


        # ----------------------------------------------------
        # PROJECTS
        # ----------------------------------------------------

        project_rows = []
        if student_row:
            cursor.execute(
                """
                SELECT
                    id,
                    student_id,
                    title,
                    description,
                    technologies,
                    github_url,
                    live_url,
                    category
                FROM projects
                WHERE student_id = %s
                ORDER BY id ASC
                """,
                (student_row[0],)
            )
            project_rows = cursor.fetchall()


        # ----------------------------------------------------
        # PORTFOLIO CONTEXT
        # ----------------------------------------------------

        settings = None
        if student_row:
            settings = portfolio_repo.get_portfolio_settings(student_row[0])

        context = portfolio_generator.format_template_context(
            student_row,
            project_rows,
            settings=settings
        )

        if request.args.get("legacy") == "1":
            return render_template(
                "index.html",
                student=context["student"],
                projects=context["projects"]
            )

        return render_template(
            "app.html",
            student=context["student"],
            projects=context["projects"],
            is_workspace_mode=False,
            is_public_view=False
        )

    except Exception as e:
        return (
            f"Database error: {e}",
            500
        )

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================
# WORKSPACE ROUTE
# ============================================================

@app.route("/workspace")
def workspace_view():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, name, email, bio, skills, education,
                resume_filename, experience, achievements,
                parser_used, headline, categorized_skills, ai_provider
            FROM students
            ORDER BY id DESC
            LIMIT 1
            """
        )
        student_row = cursor.fetchone()

        project_rows = []
        if student_row:
            cursor.execute(
                """
                SELECT id, student_id, title, description, technologies, github_url, live_url, category
                FROM projects
                WHERE student_id = %s
                ORDER BY id ASC
                """,
                (student_row[0],)
            )
            project_rows = cursor.fetchall()

        settings = None
        if student_row:
            settings = portfolio_repo.get_portfolio_settings(student_row[0])

        context = portfolio_generator.format_template_context(
            student_row,
            project_rows,
            settings=settings
        )

        return render_template(
            "app.html",
            student=context["student"],
            projects=context["projects"],
            is_workspace_mode=True,
            is_public_view=False
        )

    except Exception as e:
        return (f"Database error: {e}", 500)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================
# PUBLIC PORTFOLIO ROUTE
# ============================================================

@app.route("/p/<int:student_id>")
def public_portfolio_view(student_id: int):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id, name, email, bio, skills, education,
                resume_filename, experience, achievements,
                parser_used, headline, categorized_skills, ai_provider,
                resume_hash, processing_status, last_processed_at, user_id
            FROM students
            WHERE id = %s
            """,
            (student_id,)
        )
        student_row = cursor.fetchone()
        if not student_row:
            return ("Portfolio not found", 404)

        owner_user_id = student_row[16] if len(student_row) > 16 else None
        settings = portfolio_repo.get_portfolio_settings(student_id)

        # Check draft protection: unauthenticated or other users receive 403
        if settings and settings.get("status") == "draft":
            current_user, _ = get_current_user_from_request()
            if owner_user_id is not None:
                if not current_user or current_user["id"] != owner_user_id:
                    return ("This portfolio is currently in draft mode.", 403)

        cursor.execute(
            """
            SELECT id, student_id, title, description, technologies, github_url, live_url, category
            FROM projects
            WHERE student_id = %s
            ORDER BY id ASC
            """,
            (student_id,)
        )
        project_rows = cursor.fetchall()

        context = portfolio_generator.format_template_context(
            student_row,
            project_rows,
            settings=settings
        )

        return render_template(
            "app.html",
            student=context["student"],
            projects=context["projects"],
            is_workspace_mode=False,
            is_public_view=True
        )

    except Exception as e:
        return (f"Database error: {e}", 500)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================
# RESUME UPLOAD
# ============================================================

@app.route(
    "/upload-resume",
    methods=["POST"]
)
@rate_limit(max_per_minute=30)
def upload_resume():
    # Authentication and Ownership verification
    current_user, token_err = get_current_user_from_request()
    if token_err:
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return api_error("UNAUTHORIZED", "Authentication required.", 401)
        return ("Unauthorized", 401)

    target_student_id = request.args.get("student_id", type=int) or request.form.get("student_id", type=int)
    student_info = None
    if target_student_id:
        allowed, err_resp, student_info = check_student_ownership(target_student_id, current_user, get_db_connection)
        if not allowed:
            return err_resp

    # --------------------------------------------------------
    # 1. CHECK FILE IN REQUEST
    # --------------------------------------------------------
    if "resume" not in request.files:
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "No resume file was uploaded."}), 400
        return ("No resume file was uploaded.", 400)

    file = request.files["resume"]

    if file.filename == "":
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "No resume file was selected."}), 400
        return ("No resume file was selected.", 400)

    # --------------------------------------------------------
    # 2. CHECK EXTENSION
    # --------------------------------------------------------
    if not allowed_file(file.filename):
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": "Only PDF files are allowed."}), 400
        return ("Only PDF files are allowed.", 400)

    # --------------------------------------------------------
    # 3. SECURE ORIGINAL NAME
    # --------------------------------------------------------
    original_filename = sanitize_upload_filename(file.filename)

    # --------------------------------------------------------
    # 4. READ BYTES & VALIDATE PDF
    # --------------------------------------------------------
    try:
        file_bytes = file.read()
    except Exception as err:
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": f"Failed to read upload: {err}"}), 400
        return (f"Failed to read upload: {err}", 400)

    is_valid, validation_error = validate_pdf_content(file_bytes)
    if not is_valid:
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": validation_error}), 400
        return (validation_error, 400)

    # --------------------------------------------------------
    # 5. EXTRACT PDF TEXT
    # --------------------------------------------------------
    resume_text, extract_error = extract_pdf_text_from_bytes(file_bytes)
    if extract_error or not resume_text:
        msg = extract_error or "Could not extract text from this PDF. Please upload a text-based PDF resume."
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": msg}), 400
        return (msg, 400)

    # --------------------------------------------------------
    # 6. SAVE UNIQUE FILE TO SERVER
    # --------------------------------------------------------
    unique_filename = f"{uuid.uuid4().hex}.pdf"
    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )

    try:
        with open(file_path, "wb") as f:
            f.write(file_bytes)
    except Exception as err:
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": f"Failed to save file: {err}"}), 500
        return (f"Failed to save file: {err}", 500)

    # --------------------------------------------------------
    # 7. DATABASE RECORD
    # --------------------------------------------------------
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        target_student_id = request.args.get("student_id", type=int)
        if target_student_id:
            cursor.execute("SELECT id, user_id FROM students WHERE id = %s", (target_student_id,))
            row = cursor.fetchone()
            student_id = row[0] if row else None
            effective_user_id = row[1] if (row and row[1] is not None) else (current_user["id"] if current_user else None)
        elif current_user:
            cursor.execute("SELECT id FROM students WHERE user_id = %s ORDER BY id DESC LIMIT 1", (current_user["id"],))
            row = cursor.fetchone()
            student_id = row[0] if row else None
            effective_user_id = current_user["id"]
        else:
            cursor.execute("SELECT id FROM students WHERE user_id IS NULL ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            student_id = row[0] if row else None
            effective_user_id = None

        if not student_id:
            # Create a student record if table is currently empty
            cursor.execute(
                """
                INSERT INTO students (name, resume_filename, resume_text, processing_status, user_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                ("Your Name", original_filename, resume_text, "uploaded", effective_user_id)
            )
            student_id = cursor.fetchone()[0]
        else:
            cursor.execute(
                """
                UPDATE students
                SET
                    resume_filename = %s,
                    resume_text = %s,
                    processing_status = %s,
                    user_id = COALESCE(user_id, %s)
                WHERE id = %s
                """,
                (original_filename, resume_text, "uploaded", effective_user_id, student_id)
            )

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": f"Database error during upload: {e}"}), 500
        return (f"Resume upload failed: {e}", 500)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # --------------------------------------------------------
    # 8. AUTO-GENERATE WORKFLOW (if requested via query param)
    # --------------------------------------------------------
    auto_generate = (
        request.args.get("auto_generate", "").lower() in ("true", "1", "yes")
        or request.args.get("generate", "").lower() in ("true", "1", "yes")
    )
    if auto_generate:
        try:
            result = resume_processor.process_text(
                resume_text=resume_text,
                student_id=student_id,
                filename=original_filename,
                user_id=effective_user_id
            )
            return jsonify(result), 200
        except Exception as err:
            return jsonify({"error": f"Automatic portfolio generation failed: {err}"}), 500

    # --------------------------------------------------------
    # 9. RETURN JSON OR REDIRECT
    # --------------------------------------------------------
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            "success": True,
            "message": "Resume uploaded successfully.",
            "student_id": student_id,
            "filename": original_filename,
            "file_size": len(file_bytes)
        }), 200

    return redirect(url_for("home"))


# ============================================================
# GENERATE PORTFOLIO
# ============================================================

@app.route(
    "/generate-portfolio",
    methods=["POST"]
)
@rate_limit(max_per_minute=30)
def generate_portfolio():
    # Authentication and Ownership verification
    current_user, token_err = get_current_user_from_request()
    if token_err:
        return api_error("UNAUTHORIZED", "Authentication required.", 401)

    conn = None
    cursor = None
    try:
        req_json = request.get_json(silent=True) or {}
        student_id = req_json.get("student_id") or request.args.get("student_id", type=int)

        if student_id:
            allowed, err_resp, student_info = check_student_ownership(student_id, current_user, get_db_connection)
            if not allowed:
                return err_resp

        conn = get_db_connection()
        cursor = conn.cursor()

        if student_id:
            cursor.execute(
                """
                SELECT id, resume_text, resume_filename, user_id
                FROM students
                WHERE id = %s
                """,
                (student_id,)
            )
        elif current_user:
            cursor.execute(
                """
                SELECT id, resume_text, resume_filename, user_id
                FROM students
                WHERE user_id = %s AND resume_text IS NOT NULL AND resume_text <> ''
                ORDER BY id DESC
                LIMIT 1
                """,
                (current_user["id"],)
            )
        else:
            cursor.execute(
                """
                SELECT id, resume_text, resume_filename, user_id
                FROM students
                WHERE user_id IS NULL AND resume_text IS NOT NULL AND resume_text <> ''
                ORDER BY id DESC
                LIMIT 1
                """
            )

        student_row = cursor.fetchone()
        cursor.close()
        cursor = None
        conn.close()
        conn = None

        if not student_row:
            return jsonify({"error": "No uploaded resume was found."}), 400

        actual_student_id = student_row[0]
        resume_text = student_row[1]
        filename = student_row[2] or "resume.pdf"
        owner_id = student_row[3]

        # Guard: if student is owned by someone, check ownership
        if owner_id is not None:
            if current_user is None:
                return api_error("UNAUTHORIZED", "Authentication required.", 401)
            if current_user["id"] != owner_id:
                return api_error("FORBIDDEN", "You do not have permission to access this resource.", 403)

        if not resume_text or not resume_text.strip():
            return jsonify({"error": "Resume text is empty. Please re-upload your resume."}), 400

        # Execute end-to-end processing via ResumeProcessor
        result = resume_processor.process_text(
            resume_text=resume_text,
            student_id=actual_student_id,
            filename=filename,
            user_id=owner_id or (current_user["id"] if current_user else None)
        )

        return jsonify({
            "success": True,
            "message": "Portfolio generated successfully.",
            "student_id": actual_student_id,
            "parser_used": result["parser_used"],
            "ai_provider": result["ai_provider"],
            "confidence": result["confidence"],
            "headline": result["headline"],
            "categorized_skills": result["categorized_skills"]
        }), 200

    except Exception as e:
        print("Portfolio generation error:", e)
        return jsonify({"error": "Portfolio generation failed."}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================
# DATABASE TEST
# ============================================================

@app.route("/test-db")
def test_db():

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()


        cursor.execute(
            "SELECT version();"
        )


        version = cursor.fetchone()[0]


        return f"""
        <h2>
            Student Portfolio Database Connected! 🚀
        </h2>

        <p>
            PostgreSQL is working successfully.
        </p>

        <p>
            {version}
        </p>
        """


    except Exception as e:

        return (
            f"Database connection failed: {e}",
            500
        )


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# PHASE 2 API ENDPOINTS
# ============================================================

# ============================================================
# PHASE 2 & 3 API ENDPOINTS
# ============================================================

def _fetch_portfolio_response(student_id: Optional[int] = None):
    """Retrieve and serialize complete portfolio JSON for a specific or latest student."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if student_id is not None:
            cursor.execute("""
                SELECT
                    id, name, email, bio, skills, education, resume_filename,
                    experience, achievements, parser_used, headline, categorized_skills,
                    ai_provider, resume_hash, processing_status, last_processed_at,
                    user_id
                FROM students
                WHERE id = %s
            """, (student_id,))
        else:
            cursor.execute("""
                SELECT
                    id, name, email, bio, skills, education, resume_filename,
                    experience, achievements, parser_used, headline, categorized_skills,
                    ai_provider, resume_hash, processing_status, last_processed_at,
                    user_id
                FROM students
                ORDER BY id DESC
                LIMIT 1
            """)

        student_row = cursor.fetchone()
        if not student_row:
            return jsonify({"error": "Student not found." if student_id else "No student record found."}), 404

        actual_id = student_row[0]
        owner_user_id = student_row[16] if len(student_row) > 16 else None

        # Fetch Phase 5 portfolio settings
        settings = portfolio_repo.get_portfolio_settings(actual_id)

        # Check draft protection: unauthenticated or other users receive 403
        if settings and settings.get("status") == "draft":
            current_user, _ = get_current_user_from_request()
            if owner_user_id is not None:
                if not current_user or current_user["id"] != owner_user_id:
                    return jsonify({"error": "This portfolio is currently in draft mode."}), 403

        cursor.execute("""
            SELECT id, student_id, title, description, technologies, github_url, live_url, category
            FROM projects
            WHERE student_id = %s
            ORDER BY id ASC
        """, (actual_id,))
        project_rows = cursor.fetchall()

        # Build ResumeData
        categorized_obj = None
        if student_row[11]:
            try:
                cat_dict = json.loads(student_row[11])
                categorized_obj = CategorizedSkills(
                    languages=cat_dict.get("Programming Languages", []),
                    frameworks=cat_dict.get("Frameworks & Libraries", []),
                    databases=cat_dict.get("Databases & Storage", []),
                    tools=cat_dict.get("Developer Tools & Cloud", []),
                    apis=cat_dict.get("APIs & Protocols", []),
                    web=cat_dict.get("Web Technologies", []),
                    other=cat_dict.get("Other Skills", [])
                )
            except Exception:
                categorized_obj = None

        projects_data = []
        for p in project_rows:
            techs = [t.strip() for t in (p[4] or "").split(",") if t.strip()]
            projects_data.append(ProjectData(
                id=p[0],
                title=p[2] or "",
                description=p[3] or "",
                technologies=techs,
                github_url=p[5],
                live_url=p[6],
                category=p[7] if len(p) > 7 and p[7] else "General"
            ))

        skills_list = [s.strip() for s in (student_row[4] or "").split(",") if s.strip()]
        edu_list = [e.strip() for e in (student_row[5] or "").split("|") if e.strip()]
        exp_list = [e.strip() for e in (student_row[7] or "").split("|") if e.strip()]
        ach_list = [a.strip() for a in (student_row[8] or "").split("|") if a.strip()]

        resume_obj = ResumeData(
            name=student_row[1],
            email=student_row[2],
            summary=student_row[3],
            headline=student_row[10],
            skills=skills_list,
            categorized_skills=categorized_obj,
            education=edu_list,
            projects=projects_data,
            experience=exp_list,
            achievements=ach_list,
            parser_used=student_row[9] or "",
            ai_provider=student_row[12] or "none",
            resume_hash=student_row[13],
            processing_status=student_row[14] or "completed",
            last_processed_at=str(student_row[15]) if student_row[15] else None
        )
        resume_obj.compute_confidence()

        payload = portfolio_generator.generate_portfolio_json(resume_obj, settings=settings)
        return jsonify(payload), 200

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve portfolio: {e}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/portfolio", methods=["GET"])
def api_portfolio():
    """Return complete structured portfolio JSON for the latest student."""
    return _fetch_portfolio_response(student_id=None)


@app.route("/api/portfolio/<int:student_id>", methods=["GET"])
def api_portfolio_student(student_id):
    """Return complete structured portfolio JSON for a specific student."""
    return _fetch_portfolio_response(student_id=student_id)


def _fetch_enrichment_status(student_id: Optional[int] = None):
    """Return status and provider metadata for a specific or latest student."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if student_id is not None:
            cursor.execute("""
                SELECT id, parser_used, ai_provider, resume_hash, processing_status, last_processed_at, headline
                FROM students
                WHERE id = %s
            """, (student_id,))
        else:
            cursor.execute("""
                SELECT id, parser_used, ai_provider, resume_hash, processing_status, last_processed_at, headline
                FROM students
                ORDER BY id DESC
                LIMIT 1
            """)
        row = cursor.fetchone()
        if not row:
            return jsonify({"status": "no_resume", "error": "Student not found." if student_id else "No resume found."}), 404

        return jsonify({
            "student_id": row[0],
            "parser_used": row[1],
            "ai_provider": row[2],
            "resume_hash": row[3],
            "processing_status": row[4] or "completed",
            "last_processed_at": str(row[5]) if row[5] else None,
            "headline": row[6]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/enrichment-status", methods=["GET"])
def api_enrichment_status():
    """Return status, metadata, and provider info for the latest processed resume."""
    return _fetch_enrichment_status(student_id=None)


@app.route("/api/enrichment-status/<int:student_id>", methods=["GET"])
def api_enrichment_status_student(student_id):
    """Return status, metadata, and provider info for a specific student."""
    return _fetch_enrichment_status(student_id=student_id)


# ============================================================
# CENTRALIZED ERROR HANDLERS
# ============================================================

@app.errorhandler(400)
def handle_bad_request(error):
    if request.path.startswith("/api/v1/"):
        return api_error("BAD_REQUEST", str(getattr(error, "description", "Bad request")), 400)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": str(getattr(error, "description", "Bad request"))}), 400
    return (str(error), 400)


@app.errorhandler(401)
def handle_unauthorized(error):
    if request.path.startswith("/api/v1/"):
        return api_error("UNAUTHORIZED", "Authentication required.", 401)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Unauthorized"}), 401
    return ("Unauthorized", 401)


@app.errorhandler(403)
def handle_forbidden(error):
    if request.path.startswith("/api/v1/"):
        return api_error("FORBIDDEN", "Access forbidden.", 403)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Forbidden"}), 403
    return ("Forbidden", 403)


@app.errorhandler(404)
def handle_not_found(error):
    if request.path.startswith("/api/v1/"):
        return api_error("NOT_FOUND", "The requested resource was not found.", 404)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Not Found"}), 404
    return ("Not Found", 404)


@app.errorhandler(409)
def handle_conflict(error):
    if request.path.startswith("/api/v1/"):
        return api_error("CONFLICT", "Resource conflict occurred.", 409)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Conflict"}), 409
    return ("Conflict", 409)


@app.errorhandler(413)
def request_entity_too_large(error):
    if request.path.startswith("/api/v1/"):
        return api_error("PAYLOAD_TOO_LARGE", "File size exceeds the 10 MB limit.", 413)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "File size exceeds the 10 MB limit."}), 413
    return ("File size exceeds the 10 MB limit.", 413)


@app.errorhandler(429)
def handle_too_many_requests(error):
    if request.path.startswith("/api/v1/"):
        return api_error("RATE_LIMIT_EXCEEDED", "Rate limit exceeded. Please slow down.", 429)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Rate limit exceeded. Please slow down."}), 429
    return ("Too many requests. Please slow down.", 429)


@app.errorhandler(500)
def handle_server_error(error):
    logger.error("Internal Server Error: %s", error)
    if request.path.startswith("/api/v1/"):
        return api_error("INTERNAL_SERVER_ERROR", "An internal server error occurred.", 500)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Internal Server Error"}), 500
    return ("Internal Server Error", 500)


# ============================================================
# VERSIONED API V1 ENDPOINTS
# ============================================================

@app.route("/api/v1/auth/register", methods=["POST"])
@rate_limit(max_per_minute=20)
def api_v1_register():
    """Register a new user account with securely hashed credentials."""
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return api_error("INVALID_INPUT", "Email and password are required.", 400)

    clean_email = email.strip().lower()
    existing = user_repo.get_user_by_email(clean_email)
    if existing:
        return api_error("USER_EXISTS", "A user with this email already exists.", 409)

    try:
        user = user_repo.create_user(clean_email, password)
        logger.info("User registered: %s", clean_email)
        token = generate_auth_token(user["id"], user["email"])
        return api_success(
            data={
                "user_id": user["id"],
                "email": user["email"],
                "token": token,
                "created_at": user["created_at"]
            },
            message="User registered successfully.",
            status_code=201
        )
    except ValueError as ve:
        return api_error("VALIDATION_ERROR", str(ve), 400)
    except Exception as err:
        logger.error("User registration failed: %s", err)
        return api_error("SERVER_ERROR", "Registration failed.", 500)


@app.route("/api/v1/auth/login", methods=["POST"])
@rate_limit(max_per_minute=20)
def api_v1_login():
    """Authenticate a user account and return user profile details with JWT credential."""
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return api_error("INVALID_INPUT", "Email and password are required.", 400)

    clean_email = email.strip().lower()
    user = user_repo.get_user_by_email(clean_email)
    if not user or not user_repo.verify_password(user["password_hash"], password):
        return api_error("UNAUTHORIZED", "Invalid email or password.", 401)

    logger.info("User logged in: %s", clean_email)
    token = generate_auth_token(user["id"], user["email"])
    return api_success(
        data={
            "user_id": user["id"],
            "email": user["email"],
            "token": token
        },
        message="Authentication successful.",
        status_code=200
    )


@app.route("/api/v1/portfolio", methods=["GET"])
def api_v1_portfolio():
    """Versioned API v1: Retrieve complete portfolio JSON for the latest student."""
    resp = _fetch_portfolio_response(student_id=None)
    response_obj, code = resp if isinstance(resp, tuple) else (resp, 200)

    if code == 200:
        return api_success(data=response_obj.get_json(), status_code=200)
    err_json = response_obj.get_json() or {}
    return api_error(code="PORTFOLIO_NOT_FOUND", message=err_json.get("error", "Portfolio not found"), status_code=code)


@app.route("/api/v1/portfolio/<int:student_id>", methods=["GET"])
def api_v1_portfolio_student(student_id):
    """Versioned API v1: Retrieve complete portfolio JSON for a specific student."""
    resp = _fetch_portfolio_response(student_id=student_id)
    response_obj, code = resp if isinstance(resp, tuple) else (resp, 200)

    if code == 200:
        return api_success(data=response_obj.get_json(), status_code=200)
    err_json = response_obj.get_json() or {}
    code_str = "FORBIDDEN" if code == 403 else "STUDENT_NOT_FOUND"
    return api_error(code=code_str, message=err_json.get("error", f"Student {student_id} not found"), status_code=code)


@app.route("/api/v1/enrichment-status", methods=["GET"])
def api_v1_enrichment_status():
    """Versioned API v1: Retrieve status and AI provider metadata for latest student."""
    resp = _fetch_enrichment_status(student_id=None)
    response_obj, code = resp if isinstance(resp, tuple) else (resp, 200)

    if code == 200:
        return api_success(data=response_obj.get_json(), status_code=200)
    err_json = response_obj.get_json() or {}
    return api_error(code="NOT_FOUND", message=err_json.get("error", "No status found"), status_code=code)


@app.route("/api/v1/enrichment-status/<int:student_id>", methods=["GET"])
def api_v1_enrichment_status_student(student_id):
    """Versioned API v1: Retrieve status and AI provider metadata for specific student."""
    resp = _fetch_enrichment_status(student_id=student_id)
    response_obj, code = resp if isinstance(resp, tuple) else (resp, 200)

    if code == 200:
        return api_success(data=response_obj.get_json(), status_code=200)
    err_json = response_obj.get_json() or {}
    return api_error(code="NOT_FOUND", message=err_json.get("error", f"Student {student_id} not found"), status_code=code)


@app.route("/api/v1/resume/upload", methods=["POST"])
@rate_limit(max_per_minute=30)
def api_v1_resume_upload():
    """Versioned API v1: Securely upload, validate, parse, enrich, and generate portfolio."""
    file = request.files.get("resume") or request.files.get("file")
    if not file or not file.filename:
        return api_error("NO_FILE", "No resume file was uploaded.", 400)

    if not allowed_file(file.filename):
        return api_error("INVALID_FILE_TYPE", "Only PDF files are allowed.", 400)

    original_filename = sanitize_upload_filename(file.filename)
    try:
        file_bytes = file.read()
    except Exception as err:
        return api_error("READ_ERROR", f"Failed to read file: {err}", 400)

    is_valid, validation_error = validate_pdf_content(file_bytes)
    if not is_valid:
        return api_error("INVALID_PDF", validation_error, 400)

    resume_text, extract_error = extract_pdf_text_from_bytes(file_bytes)
    if extract_error or not resume_text:
        return api_error("EXTRACTION_ERROR", extract_error or "Could not extract text from this PDF.", 400)

    unique_filename = f"{uuid.uuid4().hex}.pdf"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    try:
        with open(file_path, "wb") as f:
            f.write(file_bytes)
    except Exception as err:
        return api_error("SAVE_ERROR", f"Failed to save file: {err}", 500)

    # Authentication and Ownership verification
    current_user, token_err = get_current_user_from_request()
    if token_err:
        return api_error("UNAUTHORIZED", "Authentication required.", 401)

    target_student_id = request.args.get("student_id", type=int) or request.form.get("student_id", type=int)
    force_refresh = request.args.get("refresh", "").lower() in ("true", "1", "yes")

    if target_student_id:
        allowed, err_resp, student_info = check_student_ownership(target_student_id, current_user, get_db_connection)
        if not allowed:
            return err_resp
        effective_user_id = student_info["user_id"] or (current_user["id"] if current_user else None)
    else:
        effective_user_id = current_user["id"] if current_user else None

    try:
        result = resume_processor.process_text(
            resume_text=resume_text,
            student_id=target_student_id,
            filename=original_filename,
            user_id=effective_user_id,
            force_refresh=force_refresh
        )
        logger.info("API v1 resume processed for student_id: %s (cached=%s)", result["student_id"], result.get("cached", False))
        return api_success(data=result, message="Resume processed successfully.", status_code=201)
    except Exception as err:
        logger.error("API v1 process_text failed: %s", err)
        return api_error("PROCESSING_ERROR", f"Processing failed: {err}", 500)


# ============================================================
# LEGACY ON-DEMAND ENRICH ROUTE
# ============================================================

@app.route("/api/enrich-resume", methods=["POST"])
@app.route("/api/v1/enrich-resume", methods=["POST"])
@rate_limit(max_per_minute=30)
def api_enrich_resume():
    """On-demand parsing and enrichment for text input or latest stored resume."""
    try:
        current_user, token_err = get_current_user_from_request()
        if token_err:
            return api_error("UNAUTHORIZED", "Authentication required.", 401)

        req_json = request.get_json(silent=True) or {}
        target_student_id = request.args.get("student_id", type=int) or req_json.get("student_id")
        if target_student_id:
            allowed, err_resp, student_info = check_student_ownership(target_student_id, current_user, get_db_connection)
            if not allowed:
                return err_resp

        text = ""
        if request.is_json:
            text = req_json.get("text", "")

        if not text:
            # Fall back to database resume text
            conn = get_db_connection()
            cursor = conn.cursor()
            if target_student_id:
                cursor.execute("SELECT resume_text, user_id FROM students WHERE id = %s", (target_student_id,))
            elif current_user:
                cursor.execute(
                    "SELECT resume_text, user_id FROM students WHERE user_id = %s AND resume_text IS NOT NULL AND resume_text <> '' ORDER BY id DESC LIMIT 1",
                    (current_user["id"],)
                )
            else:
                cursor.execute(
                    "SELECT resume_text, user_id FROM students WHERE resume_text IS NOT NULL AND resume_text <> '' ORDER BY id DESC LIMIT 1"
                )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                owner_id = row[1]
                if owner_id is not None:
                    if current_user is None:
                        return api_error("UNAUTHORIZED", "Authentication required.", 401)
                    if current_user["id"] != owner_id:
                        return api_error("FORBIDDEN", "You do not have permission to access this resource.", 403)
                text = row[0]

        if not text:
            return jsonify({"error": "No resume text provided."}), 400

        parsed, parser_name = resume_pipeline.parse(text)
        enriched = enrichment_service.enrich(parsed, resume_text=text)
        payload = portfolio_generator.generate_portfolio_json(enriched)
        return jsonify(payload), 200

    except Exception as e:
        return jsonify({"error": f"Enrichment failed: {e}"}), 500


# ============================================================
# PHASE 5: USER WORKSPACE & PORTFOLIO CUSTOMIZATION
# ============================================================

@app.route("/api/v1/me", methods=["GET"])
@require_auth
def api_v1_me():
    """Return authenticated user profile and associated student record."""
    current_user = request.current_user
    student = portfolio_repo.get_student_for_user(current_user["id"])
    return api_success(data={
        "user_id": current_user["id"],
        "email": current_user["email"],
        "student_id": student["id"] if student else None,
        "student_name": student["name"] if student else None
    })


@app.route("/api/v1/resume", methods=["GET"])
@require_auth
def api_v1_get_resume():
    """Return resume metadata for current user's student. Raw text is omitted unless requested."""
    current_user = request.current_user
    student = portfolio_repo.get_student_for_user(current_user["id"])
    if not student:
        return api_error("NOT_FOUND", "No student profile found for this user.", 404)

    student_data = student_repo.get_student_by_id(student["id"])
    if not student_data:
        return api_error("NOT_FOUND", "Student record not found.", 404)

    include_text = request.args.get("include_text", "").lower() in ("true", "1", "yes")

    resume_meta = {
        "student_id": student_data["id"],
        "resume_filename": student_data.get("resume_filename"),
        "parser_used": student_data.get("parser_used"),
        "ai_provider": student_data.get("ai_provider"),
        "processing_status": student_data.get("processing_status"),
        "last_processed_at": student_data.get("last_processed_at"),
        "has_resume": bool(student_data.get("resume_filename") or student_data.get("processing_status") == "completed")
    }

    if include_text:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT resume_text FROM students WHERE id = %s", (student["id"],))
            row = cursor.fetchone()
            resume_meta["resume_text"] = row[0] if row else ""
        finally:
            cursor.close()
            conn.close()

    return api_success(data=resume_meta)


@app.route("/api/v1/resume", methods=["DELETE"])
@require_auth
def api_v1_delete_resume():
    """Clear resume file, text, hash, and processing status while preserving profile and settings."""
    current_user = request.current_user
    student = portfolio_repo.get_student_for_user(current_user["id"])
    if not student:
        return api_error("NOT_FOUND", "No student profile found for this user.", 404)

    cleared = student_repo.clear_resume(student["id"])
    return api_success(
        data={"student_id": student["id"], "cleared": cleared},
        message="Resume cleared successfully."
    )


@app.route("/api/v1/projects", methods=["GET"])
@require_auth
def api_v1_get_projects():
    """List all projects for the authenticated user's portfolio in configured order."""
    current_user = request.current_user
    student = portfolio_repo.get_student_for_user(current_user["id"])
    if not student:
        return api_success(data=[])

    projects = project_repo.get_projects_by_student_id(student["id"])
    settings = portfolio_repo.get_portfolio_settings(student["id"])
    if settings and settings.get("project_order"):
        order_map = {pid: idx for idx, pid in enumerate(settings["project_order"])}
        projects.sort(key=lambda p: order_map.get(p.get("id"), 999999))

    return api_success(data=projects)


@app.route("/api/v1/projects", methods=["POST"])
@require_auth
def api_v1_create_project():
    """Create a new project manually for the authenticated user's portfolio."""
    current_user = request.current_user
    student = portfolio_repo.get_student_for_user(current_user["id"])
    if not student:
        # Create default student record if user hasn't uploaded a resume yet
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            name_default = current_user.get("email", "").split("@")[0] or "Student"
            cursor.execute(
                """
                INSERT INTO students (name, email, user_id, bio, parser_used)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, user_id, name, email
                """,
                (name_default, current_user.get("email", ""), current_user["id"], "", "manual")
            )
            row = cursor.fetchone()
            conn.commit()
            student = {"id": row[0], "user_id": row[1], "name": row[2], "email": row[3]}
        finally:
            cursor.close()
            conn.close()

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return api_error("VALIDATION_ERROR", "Project title is required.", 400)

    # Validate URLs if present
    for url_key in ["github_url", "live_url"]:
        val = data.get(url_key)
        if val:
            clean = val.strip().lower()
            if any(clean.startswith(s) for s in DANGEROUS_URL_SCHEMES):
                return api_error("VALIDATION_ERROR", f"Unsafe scheme in {url_key}.", 400)
            if not any(clean.startswith(s) for s in SAFE_URL_SCHEMES):
                return api_error("VALIDATION_ERROR", f"{url_key} must start with http:// or https://.", 400)

    new_project = project_repo.create_project(student["id"], data)
    return api_success(data=new_project, message="Project created successfully.", status_code=201)


@app.route("/api/v1/projects/<int:project_id>", methods=["PUT"])
@require_auth
def api_v1_update_project(project_id: int):
    """Update an existing project with user ownership enforcement."""
    current_user = request.current_user
    allowed, err_resp, proj_info = check_project_ownership(project_id, current_user, get_db_connection)
    if not allowed:
        return err_resp

    if proj_info["owner_user_id"] != current_user["id"]:
        return api_error("FORBIDDEN", "You do not have permission to modify this project.", 403)

    data = request.get_json(silent=True) or {}
    if "title" in data and not str(data["title"]).strip():
        return api_error("VALIDATION_ERROR", "Project title cannot be empty.", 400)

    # Validate URLs if present
    for url_key in ["github_url", "live_url"]:
        if url_key in data and data[url_key]:
            clean = data[url_key].strip().lower()
            if any(clean.startswith(s) for s in DANGEROUS_URL_SCHEMES):
                return api_error("VALIDATION_ERROR", f"Unsafe scheme in {url_key}.", 400)
            if not any(clean.startswith(s) for s in SAFE_URL_SCHEMES):
                return api_error("VALIDATION_ERROR", f"{url_key} must start with http:// or https://.", 400)

    updated = project_repo.update_project(project_id, data)
    return api_success(data=updated, message="Project updated successfully.")


@app.route("/api/v1/projects/<int:project_id>", methods=["DELETE"])
@require_auth
def api_v1_delete_project(project_id: int):
    """Delete an existing project with user ownership enforcement."""
    current_user = request.current_user
    allowed, err_resp, proj_info = check_project_ownership(project_id, current_user, get_db_connection)
    if not allowed:
        return err_resp

    if proj_info["owner_user_id"] != current_user["id"]:
        return api_error("FORBIDDEN", "You do not have permission to delete this project.", 403)

    deleted = project_repo.delete_project(project_id)
    return api_success(data={"project_id": project_id, "deleted": deleted}, message="Project deleted successfully.")


@app.route("/api/v1/portfolio/me", methods=["GET"])
@require_auth
def api_v1_portfolio_me():
    """Retrieve complete portfolio JSON for the authenticated user."""
    current_user = request.current_user
    student = portfolio_repo.get_student_for_user(current_user["id"])
    if not student:
        return api_error("NOT_FOUND", "No portfolio found for current user.", 404)

    return _fetch_portfolio_response(student_id=student["id"])


@app.route("/api/v1/portfolio/me/preview", methods=["GET"])
@require_auth
def api_v1_portfolio_me_preview():
    """
    Preview current portfolio with customizations applied,
    regardless of draft/published status.
    """
    current_user = request.current_user
    student = portfolio_repo.get_student_for_user(current_user["id"])
    if not student:
        return api_error("NOT_FOUND", "No portfolio found for current user.", 404)

    resp, status_code = _fetch_portfolio_response(student_id=student["id"])
    if status_code != 200:
        return resp, status_code

    payload = resp.get_json()
    payload["is_preview"] = True
    return jsonify(payload), 200


@app.route("/api/v1/portfolio", methods=["PUT"])
@require_auth
def api_v1_update_portfolio_settings():
    """
    Update customization settings for the authenticated user's portfolio.
    Fast database update only — does NOT re-run parsing or AI enrichment.
    """
    current_user = request.current_user
    student = portfolio_repo.get_student_for_user(current_user["id"])
    if not student:
        # Create default student record if user hasn't uploaded a resume yet
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            name_default = current_user.get("email", "").split("@")[0] or "Student"
            cursor.execute(
                """
                INSERT INTO students (name, email, user_id, bio, parser_used)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, user_id, name, email
                """,
                (name_default, current_user.get("email", ""), current_user["id"], "", "manual")
            )
            row = cursor.fetchone()
            conn.commit()
            student = {"id": row[0], "user_id": row[1], "name": row[2], "email": row[3]}
        finally:
            cursor.close()
            conn.close()

    data = request.get_json(silent=True) or {}
    settings_to_update = {}

    # 1. Template validation
    if "template" in data and data["template"] is not None:
        tpl = str(data["template"]).strip().lower()
        if tpl not in ALLOWED_TEMPLATES:
            return api_error("VALIDATION_ERROR", f"Invalid template '{tpl}'. Allowed: {sorted(list(ALLOWED_TEMPLATES))}.", 400)
        settings_to_update["template"] = tpl

    # 2. Theme validation
    if "theme" in data and data["theme"] is not None:
        th = str(data["theme"]).strip().lower()
        if th not in ALLOWED_THEMES:
            return api_error("VALIDATION_ERROR", f"Invalid theme '{th}'. Allowed: {sorted(list(ALLOWED_THEMES))}.", 400)
        settings_to_update["theme"] = th

    # 3. Accent validation
    if "accent" in data and data["accent"] is not None:
        acc = str(data["accent"]).strip().lower()
        if acc not in ALLOWED_ACCENTS:
            return api_error("VALIDATION_ERROR", f"Invalid accent '{acc}'. Allowed: {sorted(list(ALLOWED_ACCENTS))}.", 400)
        settings_to_update["accent"] = acc

    # 4. Status validation
    if "status" in data and data["status"] is not None:
        st = str(data["status"]).strip().lower()
        if st not in ALLOWED_STATUSES:
            return api_error("VALIDATION_ERROR", f"Invalid status '{st}'. Allowed: {sorted(list(ALLOWED_STATUSES))}.", 400)
        settings_to_update["status"] = st

    # 5. Section visibility validation
    if "section_visibility" in data:
        ok, err, cleaned_vis = validate_section_visibility(data["section_visibility"])
        if not ok:
            return api_error("VALIDATION_ERROR", err, 400)
        settings_to_update["section_visibility"] = cleaned_vis

    # 6. Project order validation
    if "project_order" in data:
        ok, err, cleaned_ord = validate_project_order(data["project_order"])
        if not ok:
            return api_error("VALIDATION_ERROR", err, 400)
        settings_to_update["project_order"] = cleaned_ord

    # 7. Social links validation
    if "social_links" in data:
        ok, err, cleaned_soc = validate_social_links(data["social_links"])
        if not ok:
            return api_error("VALIDATION_ERROR", err, 400)
        settings_to_update["social_links"] = cleaned_soc

    # 8. Custom text fields validation (length limits)
    if "custom_name" in data:
        c_name = str(data["custom_name"] or "").strip()
        if len(c_name) > 100:
            return api_error("VALIDATION_ERROR", "custom_name cannot exceed 100 characters.", 400)
        settings_to_update["custom_name"] = c_name

    if "custom_headline" in data:
        c_head = str(data["custom_headline"] or "").strip()
        if len(c_head) > 200:
            return api_error("VALIDATION_ERROR", "custom_headline cannot exceed 200 characters.", 400)
        settings_to_update["custom_headline"] = c_head

    if "custom_bio" in data:
        c_bio = str(data["custom_bio"] or "").strip()
        if len(c_bio) > 2000:
            return api_error("VALIDATION_ERROR", "custom_bio cannot exceed 2000 characters.", 400)
        settings_to_update["custom_bio"] = c_bio

    saved = portfolio_repo.save_portfolio_settings(student["id"], settings_to_update)
    return api_success(data=saved, message="Portfolio settings updated successfully.")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )