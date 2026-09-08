"""
PortfoliAI — Project Repository
Handles retrieval, safe merging, and deduplication of projects for students.
"""

from typing import Optional, Dict, Any, List
from resume_data import ProjectData


class ProjectRepository:
    """Repository managing student projects in PostgreSQL."""

    def __init__(self, db_connection_factory):
        self.get_db_connection = db_connection_factory

    def get_projects_by_student_id(self, student_id: int) -> List[Dict[str, Any]]:
        """Retrieve all projects associated with a given student_id."""
        if not student_id:
            return []

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, student_id, title, description, technologies, github_url, live_url, category
                FROM projects
                WHERE student_id = %s
                ORDER BY id ASC
                """,
                (student_id,)
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "id": r[0],
                    "student_id": r[1],
                    "title": r[2] or "",
                    "description": r[3] or "",
                    "technologies": r[4] or "",
                    "github_url": r[5],
                    "live_url": r[6],
                    "category": r[7] if len(r) > 7 and r[7] else "General"
                })
            return results
        finally:
            cursor.close()
            conn.close()

    def merge_and_save_projects(
        self,
        conn,
        student_id: int,
        enriched_projects: List[ProjectData]
    ) -> List[int]:
        """
        Merge new enriched projects with existing database projects for student_id.
        Preserves non-empty existing data when new fields are empty.
        Avoids duplicates by title match.
        """
        cursor = conn.cursor()
        try:
            # 1. Fetch existing projects for this student
            cursor.execute(
                """
                SELECT id, title, description, technologies, github_url, live_url, category
                FROM projects
                WHERE student_id = %s
                """,
                (student_id,)
            )
            existing_rows = cursor.fetchall()
            existing_by_title = {}
            for row in existing_rows:
                title_clean = (row[1] or "").strip().lower()
                if title_clean:
                    existing_by_title[title_clean] = {
                        "id": row[0],
                        "title": row[1],
                        "description": row[2],
                        "technologies": row[3],
                        "github_url": row[4],
                        "live_url": row[5],
                        "category": row[6] if len(row) > 6 else "General"
                    }

            saved_ids = []
            processed_titles = set()

            for proj in enriched_projects:
                title = proj.title.strip() if proj.title else ""
                if not title:
                    continue

                title_key = title.lower()
                processed_titles.add(title_key)

                techs_str = ", ".join(proj.technologies) if proj.technologies else None
                desc = proj.description.strip() if proj.description else None
                github = proj.github_url.strip() if proj.github_url else None
                live = proj.live_url.strip() if proj.live_url else None
                category = proj.category.strip() if proj.category else "General"

                if title_key in existing_by_title:
                    # Update existing record safely using COALESCE semantics
                    existing = existing_by_title[title_key]
                    merged_desc = desc if desc else existing["description"]
                    merged_techs = techs_str if techs_str else existing["technologies"]
                    merged_github = github if github else existing["github_url"]
                    merged_live = live if live else existing["live_url"]
                    merged_category = category if category != "General" else (existing.get("category") or "General")

                    cursor.execute(
                        """
                        UPDATE projects SET
                            description = %s,
                            technologies = %s,
                            github_url = %s,
                            live_url = %s,
                            category = %s
                        WHERE id = %s
                        """,
                        (
                            merged_desc,
                            merged_techs,
                            merged_github,
                            merged_live,
                            merged_category,
                            existing["id"]
                        )
                    )
                    saved_ids.append(existing["id"])
                else:
                    # Insert new project
                    cursor.execute(
                        """
                        INSERT INTO projects (
                            student_id, title, description, technologies, github_url, live_url, category
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            student_id,
                            title,
                            desc or "",
                            techs_str or "",
                            github,
                            live,
                            category
                        )
                    )
                    saved_ids.append(cursor.fetchone()[0])

            # Keep existing projects that were not in the new resume
            for title_key, existing in existing_by_title.items():
                if title_key not in processed_titles:
                    saved_ids.append(existing["id"])

            return saved_ids
        finally:
            cursor.close()

    def get_project_by_id(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single project by ID."""
        if not project_id:
            return None

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, student_id, title, description, technologies, github_url, live_url, category
                FROM projects
                WHERE id = %s
                """,
                (project_id,)
            )
            r = cursor.fetchone()
            if not r:
                return None
            return {
                "id": r[0],
                "student_id": r[1],
                "title": r[2] or "",
                "description": r[3] or "",
                "technologies": r[4] or "",
                "github_url": r[5],
                "live_url": r[6],
                "category": r[7] if len(r) > 7 and r[7] else "General"
            }
        finally:
            cursor.close()
            conn.close()

    def create_project(self, student_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project for a student profile."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            techs = data.get("technologies", "")
            if isinstance(techs, list):
                techs_str = ", ".join(techs)
            else:
                techs_str = str(techs or "")

            cursor.execute(
                """
                INSERT INTO projects (
                    student_id, title, description, technologies, github_url, live_url, category
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, student_id, title, description, technologies, github_url, live_url, category
                """,
                (
                    student_id,
                    data.get("title", "").strip(),
                    data.get("description", "").strip(),
                    techs_str,
                    data.get("github_url"),
                    data.get("live_url"),
                    data.get("category", "General") or "General"
                )
            )
            r = cursor.fetchone()
            conn.commit()
            return {
                "id": r[0],
                "student_id": r[1],
                "title": r[2] or "",
                "description": r[3] or "",
                "technologies": r[4] or "",
                "github_url": r[5],
                "live_url": r[6],
                "category": r[7] or "General"
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def update_project(self, project_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing project by ID."""
        existing = self.get_project_by_id(project_id)
        if not existing:
            return None

        title = data.get("title") if "title" in data else existing["title"]
        description = data.get("description") if "description" in data else existing["description"]
        if "technologies" in data:
            techs = data["technologies"]
            techs_str = ", ".join(techs) if isinstance(techs, list) else str(techs or "")
        else:
            techs_str = existing["technologies"]

        github_url = data.get("github_url") if "github_url" in data else existing["github_url"]
        live_url = data.get("live_url") if "live_url" in data else existing["live_url"]
        category = data.get("category") if "category" in data else existing["category"]

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE projects SET
                    title = %s,
                    description = %s,
                    technologies = %s,
                    github_url = %s,
                    live_url = %s,
                    category = %s
                WHERE id = %s
                RETURNING id, student_id, title, description, technologies, github_url, live_url, category
                """,
                (
                    title,
                    description,
                    techs_str,
                    github_url,
                    live_url,
                    category or "General",
                    project_id
                )
            )
            r = cursor.fetchone()
            conn.commit()
            return {
                "id": r[0],
                "student_id": r[1],
                "title": r[2] or "",
                "description": r[3] or "",
                "technologies": r[4] or "",
                "github_url": r[5],
                "live_url": r[6],
                "category": r[7] or "General"
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def delete_project(self, project_id: int) -> bool:
        """Delete a project by ID."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

