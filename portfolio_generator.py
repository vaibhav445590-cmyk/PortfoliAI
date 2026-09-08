"""
PortfoliAI — Portfolio Generation Service

Converts validated and enriched resume data into portfolio-ready structured content.
Keeps portfolio generation cleanly decoupled from parsing and database access.

Supports:
    1. Template Context Generation: Exact structure required by Jinja2 templates (index.html).
    2. Structured JSON Generation: Full portfolio payload for API clients and exports.
"""

from typing import Optional, Any
from resume_data import ResumeData, ProjectData


class PortfolioGenerator:
    """
    Dedicated service converting validated/enriched resume data
    into structured content consumable by templates and API endpoints.
    """

    @staticmethod
    def format_template_context(
        student_row: Optional[tuple],
        project_rows: list[tuple],
        settings: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Produce the exact `student` and `projects` dictionary shape expected
        by `index.html` Jinja2 rendering.
        """
        student = None

        if student_row:
            # Safe extraction handling variable column lengths
            student = {
                "id": student_row[0],
                "name": student_row[1] or "Your Name",
                "email": student_row[2] or "",
                "bio": student_row[3] or "A passionate student building projects and learning technology.",
                "skills": student_row[4] or "",
                "education": student_row[5] or "BCA",
                "resume_filename": student_row[6] or "resume.pdf",
            }
            # Optional Phase 1 & 2 columns if present in row
            if len(student_row) > 7:
                student["experience"] = student_row[7]
            if len(student_row) > 8:
                student["achievements"] = student_row[8]
            if len(student_row) > 9:
                student["parser_used"] = student_row[9]
            if len(student_row) > 10:
                student["headline"] = student_row[10]
            if len(student_row) > 11:
                student["categorized_skills"] = student_row[11]
            if len(student_row) > 12:
                student["ai_provider"] = student_row[12]

            # Apply Phase 5 settings customization if present
            if settings:
                if settings.get("custom_name"):
                    student["name"] = settings["custom_name"]
                if settings.get("custom_headline"):
                    student["headline"] = settings["custom_headline"]
                if settings.get("custom_bio"):
                    student["bio"] = settings["custom_bio"]
                student["theme"] = settings.get("theme") or "glass"
                student["accent"] = settings.get("accent") or "emerald"
                student["template"] = settings.get("template") or "default"
                student["social_links"] = settings.get("social_links") or {}
                student["section_visibility"] = settings.get("section_visibility") or {}

        projects = []

        for p in project_rows:
            proj_dict = {
                "id": p[0],
                "student_id": p[1],
                "title": p[2] or "",
                "description": p[3] or "",
                "technologies": p[4] or "",
                "github_url": p[5],
                "live_url": p[6],
            }
            if len(p) > 7:
                proj_dict["category"] = p[7]
            projects.append(proj_dict)

        if settings and settings.get("project_order"):
            order_map = {pid: idx for idx, pid in enumerate(settings["project_order"])}
            projects.sort(key=lambda p: order_map.get(p.get("id"), 999999))

        return {
            "student": student,
            "projects": projects
        }

    @staticmethod
    def generate_portfolio_json(
        resume: ResumeData,
        settings: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Produce a comprehensive, structured portfolio JSON document
        from an enriched ResumeData instance, optionally overlaid with
        user customization settings.
        """
        name = (settings.get("custom_name") if settings and settings.get("custom_name") else None) or resume.name or "Your Name"
        headline = (settings.get("custom_headline") if settings and settings.get("custom_headline") else None) or resume.headline or "Developer · Creator"
        bio = (settings.get("custom_bio") if settings and settings.get("custom_bio") else None) or resume.summary or "A passionate developer building projects and learning technology."

        customization_block = {
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
                "achievements": True
            },
            "project_order": [],
            "social_links": {}
        }

        if settings:
            for key in ["template", "theme", "accent", "status", "section_visibility", "project_order", "social_links"]:
                if key in settings and settings[key] is not None:
                    customization_block[key] = settings[key]

        avatar_letter = (name.strip()[0].upper()) if name and name.strip() else "V"

        categorized_dict = (
            resume.categorized_skills.to_dict()
            if resume.categorized_skills
            else {}
        )

        projects_list = []
        for p in resume.projects:
            proj_dict = {
                "title": p.title,
                "description": p.description,
                "category": p.category,
                "technologies": p.technologies,
                "technologies_str": ", ".join(p.technologies),
                "github_url": p.github_url,
                "live_url": p.live_url,
            }
            if getattr(p, "id", None) is not None:
                proj_dict["id"] = p.id
            projects_list.append(proj_dict)

        if customization_block.get("project_order"):
            order_map = {pid: idx for idx, pid in enumerate(customization_block["project_order"])}
            projects_list.sort(key=lambda p: order_map.get(p.get("id"), 999999))

        return {
            "profile": {
                "name": name,
                "headline": headline,
                "email": resume.email or "",
                "phone": resume.phone or "",
                "bio": bio,
                "avatar_letter": avatar_letter,
                "education": resume.education,
                "education_str": resume.education_text(),
                "social_links": customization_block.get("social_links", {}),
            },
            "stats": {
                "projects_count": len(resume.projects),
                "skills_count": len(resume.skills),
                "has_experience": len(resume.experience) > 0,
                "has_achievements": len(resume.achievements) > 0,
            },
            "skills": {
                "all": resume.skills,
                "categorized": categorized_dict,
            },
            "projects": projects_list,
            "experience": resume.experience,
            "achievements": resume.achievements,
            "customization": customization_block,
            "status": customization_block.get("status", "published"),
            "is_draft": (customization_block.get("status") == "draft"),
            "metadata": {
                "parser_used": resume.parser_used,
                "ai_provider": resume.ai_provider,
                "confidence": resume.confidence,
                "processing_status": resume.processing_status,
                "last_processed_at": resume.last_processed_at,
                "resume_hash": resume.resume_hash,
            }
        }
