"""
PortfoliAI — Student Repository
Handles database persistence, safe updates (COALESCE protection), and retrieval for students.
"""

from typing import Optional, Dict, Any, List
import json
import hashlib
from datetime import datetime, timezone
from resume_data import ResumeData, CategorizedSkills


class StudentRepository:
    """Repository managing student records in PostgreSQL."""

    def __init__(self, db_connection_factory):
        self.get_db_connection = db_connection_factory

    def get_student_by_id(self, student_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve student record by student_id."""
        if not student_id:
            return None

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    id, name, email, bio, skills, education, resume_filename,
                    experience, achievements, parser_used, headline, categorized_skills,
                    ai_provider, resume_hash, processing_status, last_processed_at,
                    user_id
                FROM students
                WHERE id = %s
                """,
                (student_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)
        finally:
            cursor.close()
            conn.close()

    def get_latest_student(self, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Retrieve the most recent student record, optionally filtered by user_id."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            if user_id is not None:
                cursor.execute(
                    """
                    SELECT
                        id, name, email, bio, skills, education, resume_filename,
                        experience, achievements, parser_used, headline, categorized_skills,
                        ai_provider, resume_hash, processing_status, last_processed_at,
                        user_id
                    FROM students
                    WHERE user_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_id,)
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        id, name, email, bio, skills, education, resume_filename,
                        experience, achievements, parser_used, headline, categorized_skills,
                        ai_provider, resume_hash, processing_status, last_processed_at,
                        user_id
                    FROM students
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)
        finally:
            cursor.close()
            conn.close()

    def get_student_by_resume_hash(
        self,
        resume_hash: str,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find a previously processed student with identical resume content.
        Used for performance caching to avoid redundant re-parsing.
        """
        if not resume_hash:
            return None

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            if user_id is not None:
                cursor.execute(
                    """
                    SELECT
                        id, name, email, bio, skills, education, resume_filename,
                        experience, achievements, parser_used, headline, categorized_skills,
                        ai_provider, resume_hash, processing_status, last_processed_at,
                        user_id
                    FROM students
                    WHERE resume_hash = %s AND user_id = %s AND processing_status = 'completed'
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (resume_hash, user_id)
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        id, name, email, bio, skills, education, resume_filename,
                        experience, achievements, parser_used, headline, categorized_skills,
                        ai_provider, resume_hash, processing_status, last_processed_at,
                        user_id
                    FROM students
                    WHERE resume_hash = %s AND processing_status = 'completed'
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (resume_hash,)
                )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)
        finally:
            cursor.close()
            conn.close()

    def save_or_update_student(
        self,
        conn,
        enriched_data: ResumeData,
        parser_name: str,
        student_id: Optional[int] = None,
        user_id: Optional[int] = None,
        filename: Optional[str] = None,
        resume_text: Optional[str] = None,
        resume_hash: Optional[str] = None
    ) -> int:
        """
        Persist or update student profile using the provided open connection and transaction.
        Implements safe COALESCE updates to prevent overwriting existing valid data with empty values.
        """
        cursor = conn.cursor()
        try:
            # Prepare data values
            name_val = enriched_data.name if enriched_data.name and enriched_data.name.strip() else None
            email_val = enriched_data.email if enriched_data.email and enriched_data.email.strip() else None
            bio_val = enriched_data.summary if enriched_data.summary and enriched_data.summary.strip() else None
            skills_val = ", ".join(enriched_data.skills) if enriched_data.skills else None
            edu_val = " | ".join(enriched_data.education) if enriched_data.education else None
            exp_val = " | ".join(enriched_data.experience) if enriched_data.experience else None
            ach_val = " | ".join(enriched_data.achievements) if enriched_data.achievements else None
            headline_val = enriched_data.headline if enriched_data.headline and enriched_data.headline.strip() else None
            cat_skills_val = enriched_data.categorized_skills.to_json() if enriched_data.categorized_skills else None
            ai_provider_val = enriched_data.ai_provider or "none"
            status_val = enriched_data.processing_status or "completed"
            processed_at = datetime.now(timezone.utc)

            # Compute resume hash if not provided
            if not resume_hash and resume_text:
                resume_hash = hashlib.sha256(resume_text.encode("utf-8")).hexdigest()

            if student_id is not None:
                cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
                if not cursor.fetchone():
                    student_id = None

            # If student_id is not provided, check if email already exists
            if student_id is None and email_val:
                cursor.execute("SELECT id FROM students WHERE email = %s", (email_val,))
                email_row = cursor.fetchone()
                if email_row:
                    student_id = email_row[0]

            if student_id is None:
                cursor.execute(
                    """
                    INSERT INTO students (
                        name, email, bio, skills, education,
                        experience, achievements, parser_used,
                        headline, categorized_skills, ai_provider,
                        resume_hash, processing_status, last_processed_at,
                        resume_filename, resume_text, user_id
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s
                    )
                    RETURNING id
                    """,
                    (
                        name_val, email_val, bio_val, skills_val, edu_val,
                        exp_val, ach_val, parser_name,
                        headline_val, cat_skills_val, ai_provider_val,
                        resume_hash, status_val, processed_at,
                        filename, resume_text, user_id
                    )
                )
                actual_id = cursor.fetchone()[0]
            else:
                cursor.execute(
                    """
                    UPDATE students SET
                        name = COALESCE(NULLIF(%s, ''), name),
                        email = COALESCE(NULLIF(%s, ''), email),
                        bio = COALESCE(NULLIF(%s, ''), bio),
                        skills = COALESCE(NULLIF(%s, ''), skills),
                        education = COALESCE(NULLIF(%s, ''), education),
                        experience = COALESCE(NULLIF(%s, ''), experience),
                        achievements = COALESCE(NULLIF(%s, ''), achievements),
                        parser_used = COALESCE(NULLIF(%s, ''), parser_used),
                        headline = COALESCE(NULLIF(%s, ''), headline),
                        categorized_skills = COALESCE(NULLIF(%s, ''), categorized_skills),
                        ai_provider = COALESCE(NULLIF(%s, ''), ai_provider),
                        resume_hash = COALESCE(NULLIF(%s, ''), resume_hash),
                        processing_status = %s,
                        last_processed_at = %s,
                        resume_filename = COALESCE(NULLIF(%s, ''), resume_filename),
                        resume_text = COALESCE(NULLIF(%s, ''), resume_text),
                        user_id = COALESCE(%s, user_id)
                    WHERE id = %s
                    """,
                    (
                        name_val or "", email_val or "", bio_val or "", skills_val or "", edu_val or "",
                        exp_val or "", ach_val or "", parser_name or "",
                        headline_val or "", cat_skills_val or "", ai_provider_val or "",
                        resume_hash or "", status_val, processed_at,
                        filename or "", resume_text or "", user_id,
                        student_id
                    )
                )
                actual_id = student_id

            return actual_id
        finally:
            cursor.close()

    @staticmethod
    def _row_to_dict(row: tuple) -> Dict[str, Any]:
        """Convert a database tuple into a structured student dict."""
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "bio": row[3],
            "skills": row[4],
            "education": row[5],
            "resume_filename": row[6],
            "experience": row[7],
            "achievements": row[8],
            "parser_used": row[9],
            "headline": row[10],
            "categorized_skills": row[11],
            "ai_provider": row[12],
            "resume_hash": row[13],
            "processing_status": row[14],
            "last_processed_at": str(row[15]) if row[15] else None,
            "user_id": row[16] if len(row) > 16 else None,
        }

    def clear_resume(self, student_id: int) -> bool:
        """
        Clears the resume text, filename, hash, and resets processing status to 'pending'
        without deleting the student record or their custom portfolio settings.
        Returns True if the record was updated, False if student_id not found.
        """
        if not student_id:
            return False

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE students SET
                    resume_filename = NULL,
                    resume_text = NULL,
                    resume_hash = NULL,
                    processing_status = 'pending',
                    last_processed_at = NULL
                WHERE id = %s
                """,
                (student_id,)
            )
            updated = cursor.rowcount > 0
            conn.commit()
            return updated
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
