"""
PortfoliAI — Modular Resume Processor & Pipeline Orchestrator

Encapsulates the end-to-end resume processing lifecycle:
    1. PDF Validation & Extraction:
       - File format, magic-byte (%PDF-), and size verification
       - Text extraction via pypdf with robust error recovery
    2. Parsing & Validation:
       - Structured parsing via Phase 1 parser pipeline
       - Pydantic model validation and normalization
    3. AI / Local Enrichment:
       - Provider-agnostic enrichment via Phase 2 AI layer
       - Local fallback without hallucinations
    4. Safe Database Persistence:
       - Student profile insertion / safe COALESCE updates
       - Project collection merging, deduplication, and unparsed project retention
    5. Portfolio Generation:
       - Conversion to portfolio-ready structured context & JSON
"""

import os
import io
import uuid
import hashlib
import json
from typing import Optional, Tuple, Dict, Any, List
import psycopg2
from pypdf import PdfReader
from pypdf.errors import PdfStreamError

from resume_data import ResumeData, ProjectData, CategorizedSkills
from parser_pipeline import ParserPipeline
from ai.enrichment_service import EnrichmentService
from portfolio_generator import PortfolioGenerator


# ============================================================
# 1. PDF VALIDATION & EXTRACTION
# ============================================================

MAX_RESUME_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_pdf_content(file_bytes: bytes) -> Tuple[bool, str]:
    """
    Validate that the provided raw bytes represent a legitimate, readable PDF.
    Checks:
        - Minimum length
        - Magic bytes header (%PDF-)
        - Valid syntax loadable by pypdf
    """
    if not file_bytes or len(file_bytes) == 0:
        return False, "The uploaded file is empty (0 bytes)."

    if len(file_bytes) > MAX_RESUME_BYTES:
        return False, "File size exceeds the 10 MB limit."

    # Look for PDF magic header in the first 1024 bytes (standard PDF specification)
    header_sample = file_bytes[:1024]
    if b"%PDF-" not in header_sample:
        return False, "Invalid PDF header. The uploaded file is not a valid PDF document."

    try:
        stream = io.BytesIO(file_bytes)
        reader = PdfReader(stream)
        if len(reader.pages) == 0:
            return False, "The PDF document contains no pages."
    except (PdfStreamError, Exception) as err:
        return False, f"Corrupted or unreadable PDF: {err}"

    return True, ""


def extract_pdf_text_from_bytes(file_bytes: bytes) -> Tuple[str, str]:
    """
    Extract all readable text across all pages from PDF bytes.
    Returns:
        (extracted_text, error_message)
    """
    is_valid, error = validate_pdf_content(file_bytes)
    if not is_valid:
        return "", error

    try:
        stream = io.BytesIO(file_bytes)
        reader = PdfReader(stream)
        extracted = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                extracted.append(text.strip())

        full_text = "\n\n".join(extracted).strip()
        if not full_text:
            return "", "Could not extract text from this PDF. Please upload a text-based PDF resume (scanned image PDFs without OCR are not supported)."

        return full_text, ""
    except Exception as err:
        return "", f"Failed to extract text from PDF: {err}"


def extract_pdf_text_from_file(file_path: str) -> Tuple[str, str]:
    """
    Extract readable text from a PDF file located at file_path.
    """
    if not os.path.exists(file_path):
        return "", f"File not found: {file_path}"

    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return extract_pdf_text_from_bytes(data)
    except Exception as err:
        return "", f"Error reading file {file_path}: {err}"


# ============================================================
# 2. DATABASE PERSISTENCE LAYER (Safe COALESCE & Merging)
# ============================================================

def persist_student_data(
    conn,
    enriched_data: ResumeData,
    parser_name: str,
    student_id: Optional[int] = None,
    filename: Optional[str] = None,
    resume_text: Optional[str] = None,
    user_id: Optional[int] = None
) -> int:
    """
    Persist student profile into PostgreSQL.
    If student_id is provided, updates existing record using COALESCE to protect
    valid database data from empty values.
    If student_id is None, creates a new student record and returns the assigned id.
    """
    cursor = conn.cursor()
    try:
        if student_id is not None:
            # Check student exists
            cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
            if not cursor.fetchone():
                student_id = None  # Fall through to insert if ID not found

        # If student_id is not given, check if a student with this email already exists
        if student_id is None and enriched_data.email and enriched_data.email.strip():
            cursor.execute("SELECT id FROM students WHERE email = %s", (enriched_data.email.strip(),))
            email_row = cursor.fetchone()
            if email_row:
                student_id = email_row[0]

        email_to_use = enriched_data.email.strip() if (enriched_data.email and enriched_data.email.strip()) else None
        if not email_to_use and user_id:
            cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
            urow = cursor.fetchone()
            if urow and urow[0]:
                email_to_use = urow[0]
        if not email_to_use:
            email_to_use = f"student_{uuid.uuid4().hex[:10]}@example.com"

        if student_id is None:
            # Insert brand new student
            cursor.execute(
                """
                INSERT INTO students (
                    name, email, bio, skills, education,
                    experience, achievements, parser_used,
                    headline, categorized_skills, ai_provider,
                    resume_hash, processing_status, last_processed_at,
                    resume_filename, resume_text, user_id
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, NOW(),
                    %s, %s, %s
                )
                RETURNING id
                """,
                (
                    enriched_data.name or "Your Name",
                    email_to_use,
                    enriched_data.summary or "",
                    enriched_data.skills_text(),
                    enriched_data.education_text(),
                    enriched_data.experience_text(),
                    enriched_data.achievements_text(),
                    parser_name,
                    enriched_data.headline or "",
                    enriched_data.categorized_skills_json(),
                    enriched_data.ai_provider or "none",
                    enriched_data.resume_hash or "",
                    "completed",
                    filename or "resume.pdf",
                    resume_text or "",
                    user_id
                )
            )
            student_id = cursor.fetchone()[0]
        else:
            # Check if updating email would collide with another student
            email_param = enriched_data.email.strip() if (enriched_data.email and enriched_data.email.strip()) else ""
            if email_param:
                cursor.execute("SELECT id FROM students WHERE email = %s AND id <> %s", (email_param, student_id))
                if cursor.fetchone():
                    # Another student record already has this email!
                    cursor.execute("SELECT email FROM students WHERE id = %s", (student_id,))
                    cur_row = cursor.fetchone()
                    if cur_row and cur_row[0]:
                        email_param = ""  # keeps existing valid email via COALESCE
                    else:
                        email_param = f"student_{student_id}_{uuid.uuid4().hex[:6]}@example.com"

            # Update existing student with COALESCE safety
            cursor.execute(
                """
                UPDATE students
                SET
                    name               = COALESCE(NULLIF(%s, ''), name),
                    email              = COALESCE(NULLIF(%s, ''), email),
                    bio                = COALESCE(NULLIF(%s, ''), bio),
                    skills             = COALESCE(NULLIF(%s, ''), skills),
                    education          = COALESCE(NULLIF(%s, ''), education),
                    experience         = COALESCE(NULLIF(%s, ''), experience),
                    achievements       = COALESCE(NULLIF(%s, ''), achievements),
                    parser_used        = COALESCE(NULLIF(%s, ''), parser_used),
                    headline           = COALESCE(NULLIF(%s, ''), headline),
                    categorized_skills = COALESCE(NULLIF(%s, ''), categorized_skills),
                    ai_provider        = COALESCE(NULLIF(%s, ''), ai_provider),
                    resume_hash        = COALESCE(NULLIF(%s, ''), resume_hash),
                    resume_filename    = COALESCE(NULLIF(%s, ''), resume_filename),
                    resume_text        = COALESCE(NULLIF(%s, ''), resume_text),
                    user_id            = COALESCE(%s, user_id),
                    processing_status  = %s,
                    last_processed_at  = NOW()
                WHERE id = %s
                """,
                (
                    enriched_data.name or "",
                    email_param,
                    enriched_data.summary or "",
                    enriched_data.skills_text(),
                    enriched_data.education_text(),
                    enriched_data.experience_text(),
                    enriched_data.achievements_text(),
                    parser_name,
                    enriched_data.headline or "",
                    enriched_data.categorized_skills_json(),
                    enriched_data.ai_provider or "",
                    enriched_data.resume_hash or "",
                    filename or "",
                    resume_text or "",
                    user_id,
                    "completed",
                    student_id
                )
            )

        return student_id
    finally:
        cursor.close()


def persist_project_data(
    conn,
    student_id: int,
    enriched_projects: List[ProjectData]
) -> List[int]:
    """
    Persist project records safely for a student:
    - If parsed project list is empty, DO NOT delete existing projects.
    - If parsed projects exist, merges with existing database projects:
      - Preserves existing technologies if newly parsed has none.
      - Preserves existing github_url, live_url, description if newly parsed has none.
      - Preserves projects that exist in DB but were omitted in re-parsing.
      - Avoids creating duplicate project entries.
    """
    cursor = conn.cursor()
    saved_ids = []
    try:
        valid_projects = [
            p for p in enriched_projects
            if p.title and p.title.strip()
        ]

        # Guard: If no valid projects parsed, do not touch existing DB projects
        if not valid_projects:
            cursor.execute("SELECT id FROM projects WHERE student_id = %s", (student_id,))
            return [row[0] for row in cursor.fetchall()]

        # Retrieve existing projects for this student
        cursor.execute(
            """
            SELECT id, title, description, technologies, github_url, live_url, category
            FROM projects
            WHERE student_id = %s
            """,
            (student_id,)
        )
        existing_rows = cursor.fetchall()
        existing_by_title: Dict[str, Dict[str, Any]] = {}
        for row in existing_rows:
            if row[1]:
                norm = row[1].strip().lower()
                existing_by_title[norm] = {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2] or "",
                    "technologies": row[3] or "",
                    "github_url": row[4],
                    "live_url": row[5],
                    "category": row[6] if len(row) > 6 and row[6] else "General"
                }

        # Clear existing rows for this student to cleanly re-insert the merged set
        cursor.execute("DELETE FROM projects WHERE student_id = %s", (student_id,))

        seen_titles = set()

        for project in valid_projects:
            norm_title = project.title.strip().lower()
            seen_titles.add(norm_title)
            existing = existing_by_title.get(norm_title, {})

            # Technologies: newly parsed list takes precedence, fallback to existing
            techs = list(project.technologies) if project.technologies else []
            if not techs and existing.get("technologies"):
                techs = [t.strip() for t in existing["technologies"].split(",") if t.strip()]
            technologies_text = ", ".join(techs)

            description = (
                project.description.strip()
                if project.description and project.description.strip()
                else existing.get("description", "")
            )

            github_url = project.github_url if project.github_url else existing.get("github_url")
            live_url = project.live_url if project.live_url else existing.get("live_url")
            category = (
                project.category
                if project.category and project.category != "General"
                else existing.get("category", "General")
            )

            cursor.execute(
                """
                INSERT INTO projects (
                    student_id, title, description, technologies,
                    github_url, live_url, category
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    student_id,
                    project.title.strip(),
                    description,
                    technologies_text,
                    github_url,
                    live_url,
                    category
                )
            )
            saved_ids.append(cursor.fetchone()[0])

        # Preserve any unparsed existing projects not present in newly parsed resume
        for norm_title, existing in existing_by_title.items():
            if norm_title not in seen_titles:
                cursor.execute(
                    """
                    INSERT INTO projects (
                        student_id, title, description, technologies,
                        github_url, live_url, category
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        student_id,
                        existing["title"],
                        existing["description"],
                        existing["technologies"],
                        existing["github_url"],
                        existing["live_url"],
                        existing.get("category", "General")
                    )
                )
                saved_ids.append(cursor.fetchone()[0])

        return saved_ids
    finally:
        cursor.close()


# ============================================================
# 3. PIPELINE ORCHESTRATOR (ResumeProcessor)
# ============================================================

class ResumeProcessor:
    """
    High-level orchestrator executing the end-to-end processing lifecycle:
    Extract -> Parse -> Validate -> Enrich -> Persist -> Generate.
    """

    def __init__(
        self,
        pipeline: ParserPipeline,
        enrichment_service: EnrichmentService,
        portfolio_generator: PortfolioGenerator,
        db_connection_factory
    ):
        self.pipeline = pipeline
        self.enrichment_service = enrichment_service
        self.portfolio_generator = portfolio_generator
        self.get_db_connection = db_connection_factory

    def process_text(
        self,
        resume_text: str,
        student_id: Optional[int] = None,
        filename: Optional[str] = None,
        user_id: Optional[int] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline from extracted resume text:
            1. Check cache (by resume_hash if student already processed)
            2. Parse via Phase 1 pipeline
            3. Validate Pydantic model
            4. Enrich via Phase 2 AI layer
            5. Persist to PostgreSQL with safe merging & indexing
            6. Generate portfolio JSON
        """
        if not resume_text or not resume_text.strip():
            raise ValueError("Empty resume text cannot be processed.")

        resume_hash = hashlib.sha256(resume_text.encode("utf-8")).hexdigest()

        # Check performance cache if not forcing refresh
        if not force_refresh and student_id is not None:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT id, name, email, bio, skills, education, resume_filename,
                           experience, achievements, parser_used, headline, categorized_skills,
                           ai_provider, resume_hash, processing_status, last_processed_at
                    FROM students
                    WHERE id = %s AND resume_hash = %s AND processing_status = 'completed'
                    """,
                    (student_id, resume_hash)
                )
                student_row = cursor.fetchone()
                if student_row:
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

                    cached_resume = ResumeData(
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
                        parser_used=student_row[9] or "cached",
                        ai_provider=student_row[12] or "none",
                        resume_hash=student_row[13],
                        processing_status="completed",
                        last_processed_at=str(student_row[15]) if student_row[15] else None
                    )
                    cached_resume.compute_confidence()
                    portfolio_payload = self.portfolio_generator.generate_portfolio_json(cached_resume)

                    return {
                        "success": True,
                        "message": "Portfolio retrieved from cache.",
                        "student_id": student_id,
                        "parser_used": student_row[9] or "cached",
                        "ai_provider": student_row[12] or "none",
                        "confidence": cached_resume.confidence,
                        "headline": student_row[10],
                        "categorized_skills": categorized_obj.to_dict() if categorized_obj else {},
                        "portfolio": portfolio_payload,
                        "cached": True
                    }
            finally:
                cursor.close()
                conn.close()

        # 1. Parse
        parsed_data, parser_name = self.pipeline.parse(resume_text)

        # 2. Enrich
        enriched_data = self.enrichment_service.enrich(
            parsed_data,
            resume_text=resume_text
        )
        enriched_data.resume_hash = resume_hash

        # 3. Persist
        conn = self.get_db_connection()
        try:
            actual_student_id = persist_student_data(
                conn=conn,
                enriched_data=enriched_data,
                parser_name=parser_name,
                student_id=student_id,
                filename=filename,
                resume_text=resume_text,
                user_id=user_id
            )
            persist_project_data(
                conn=conn,
                student_id=actual_student_id,
                enriched_projects=enriched_data.projects
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        # 4. Generate portfolio JSON
        portfolio_payload = self.portfolio_generator.generate_portfolio_json(enriched_data)

        categorized_dict = (
            enriched_data.categorized_skills.to_dict()
            if enriched_data.categorized_skills
            else {}
        )

        return {
            "success": True,
            "message": "Portfolio generated successfully.",
            "student_id": actual_student_id,
            "parser_used": parser_name,
            "ai_provider": enriched_data.ai_provider,
            "confidence": enriched_data.confidence,
            "headline": enriched_data.headline,
            "categorized_skills": categorized_dict,
            "portfolio": portfolio_payload,
            "cached": False
        }
