"""
PortfoliAI — Portfolio Settings Repository
Manages database persistence, defaults, and retrieval for portfolio customization,
theming, template selection, section visibility, project ordering, and social links.
"""

from typing import Optional, Dict, Any, List
import json
from datetime import datetime, timezone


DEFAULT_SETTINGS: Dict[str, Any] = {
    "template": "default",
    "theme": "glass",
    "accent": "emerald",
    "status": "published",
    "section_visibility": {
        "about": True,
        "skills": True,
        "education": True,
        "experience": True,
        "projects": True,
        "achievements": True,
    },
    "project_order": [],
    "social_links": {},
    "custom_headline": None,
    "custom_bio": None,
    "custom_name": None,
}


class PortfolioRepository:
    """Repository managing portfolio_settings in PostgreSQL."""

    def __init__(self, db_connection_factory):
        self.get_db_connection = db_connection_factory

    def get_settings_by_student_id(self, student_id: int) -> Dict[str, Any]:
        """
        Retrieve customization settings for a given student_id.
        If no record exists, returns standard defaults.
        """
        if not student_id:
            return dict(DEFAULT_SETTINGS)

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT
                    id, student_id, template, theme, accent, status,
                    section_visibility, project_order, social_links,
                    custom_headline, custom_bio, custom_name,
                    created_at, updated_at
                FROM portfolio_settings
                WHERE student_id = %s
                """,
                (student_id,)
            )
            row = cursor.fetchone()
            if not row:
                res = dict(DEFAULT_SETTINGS)
                res["student_id"] = student_id
                return res

            return self._row_to_dict(row)
        finally:
            cursor.close()
            conn.close()

    def upsert_settings(
        self,
        student_id: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atomically update or insert customization settings for a student.
        Merges provided updates with existing or default values.
        """
        existing = self.get_settings_by_student_id(student_id)

        template = updates.get("template", existing.get("template", "default"))
        theme = updates.get("theme", existing.get("theme", "glass"))
        accent = updates.get("accent", existing.get("accent", "emerald"))
        status = updates.get("status", existing.get("status", "published"))

        # Section visibility merge
        sec_vis = dict(existing.get("section_visibility") or DEFAULT_SETTINGS["section_visibility"])
        if "section_visibility" in updates and isinstance(updates["section_visibility"], dict):
            sec_vis.update(updates["section_visibility"])

        # Project order
        proj_order = updates.get("project_order")
        if proj_order is None:
            proj_order = existing.get("project_order", [])

        # Social links merge
        soc_links = dict(existing.get("social_links") or {})
        if "social_links" in updates and isinstance(updates["social_links"], dict):
            soc_links = updates["social_links"]

        # Custom text fields (allow explicit None/empty)
        custom_headline = updates.get("custom_headline") if "custom_headline" in updates else existing.get("custom_headline")
        custom_bio = updates.get("custom_bio") if "custom_bio" in updates else existing.get("custom_bio")
        custom_name = updates.get("custom_name") if "custom_name" in updates else existing.get("custom_name")

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO portfolio_settings (
                    student_id, template, theme, accent, status,
                    section_visibility, project_order, social_links,
                    custom_headline, custom_bio, custom_name,
                    updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    NOW()
                )
                ON CONFLICT (student_id) DO UPDATE SET
                    template = EXCLUDED.template,
                    theme = EXCLUDED.theme,
                    accent = EXCLUDED.accent,
                    status = EXCLUDED.status,
                    section_visibility = EXCLUDED.section_visibility,
                    project_order = EXCLUDED.project_order,
                    social_links = EXCLUDED.social_links,
                    custom_headline = EXCLUDED.custom_headline,
                    custom_bio = EXCLUDED.custom_bio,
                    custom_name = EXCLUDED.custom_name,
                    updated_at = NOW()
                RETURNING
                    id, student_id, template, theme, accent, status,
                    section_visibility, project_order, social_links,
                    custom_headline, custom_bio, custom_name,
                    created_at, updated_at
                """,
                (
                    student_id,
                    template,
                    theme,
                    accent,
                    status,
                    json.dumps(sec_vis),
                    json.dumps(proj_order),
                    json.dumps(soc_links),
                    custom_headline,
                    custom_bio,
                    custom_name
                )
            )
            row = cursor.fetchone()
            conn.commit()
            return self._row_to_dict(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def get_student_for_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the primary student profile belonging to an authenticated user."""
        if not user_id:
            return None

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, name, email, user_id, resume_filename, resume_hash, processing_status
                FROM students
                WHERE user_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "user_id": row[3],
                "resume_filename": row[4],
                "resume_hash": row[5],
                "processing_status": row[6]
            }
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def _row_to_dict(row: tuple) -> Dict[str, Any]:
        """Convert database tuple to dictionary with parsed JSON fields."""
        def _parse_json(val, default):
            if val is None:
                return default
            if isinstance(val, (dict, list)):
                return val
            try:
                return json.loads(val)
            except Exception:
                return default

        return {
            "id": row[0],
            "student_id": row[1],
            "template": row[2] or "default",
            "theme": row[3] or "glass",
            "accent": row[4] or "emerald",
            "status": row[5] or "published",
            "section_visibility": _parse_json(row[6], DEFAULT_SETTINGS["section_visibility"]),
            "project_order": _parse_json(row[7], []),
            "social_links": _parse_json(row[8], {}),
            "custom_headline": row[9],
            "custom_bio": row[10],
            "custom_name": row[11],
            "created_at": str(row[12]) if row[12] else None,
            "updated_at": str(row[13]) if row[13] else None,
        }

    def get_portfolio_settings(self, student_id: int) -> Dict[str, Any]:
        """Convenience alias for get_settings_by_student_id."""
        return self.get_settings_by_student_id(student_id)

    def save_portfolio_settings(self, student_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience alias for upsert_settings."""
        return self.upsert_settings(student_id, updates)
