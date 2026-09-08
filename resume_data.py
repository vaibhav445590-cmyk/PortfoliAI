"""
PortfoliAI — Resume Data Models

Pydantic models that define the validated shape of parsed
and enriched resume data. Every parser and AI enrichment service
in the pipeline produces and validates against these models.
"""

from pydantic import BaseModel, field_validator
from typing import Optional
import json


# ============================================================
# SKILL CATEGORIES
# ============================================================

class CategorizedSkills(BaseModel):
    """
    Intelligently grouped skills for portfolio presentation.
    Preserves all original skills while organizing them into
    meaningful technical categories.
    """

    languages: list[str] = []
    frameworks: list[str] = []
    databases: list[str] = []
    tools: list[str] = []
    apis: list[str] = []
    web: list[str] = []
    other: list[str] = []

    def all_skills(self) -> list[str]:
        """Return a flat list of all categorized skills."""
        combined = (
            self.languages
            + self.frameworks
            + self.databases
            + self.tools
            + self.apis
            + self.web
            + self.other
        )
        seen = set()
        result = []
        for s in combined:
            if s.lower() not in seen:
                seen.add(s.lower())
                result.append(s)
        return result

    def to_dict(self) -> dict[str, list[str]]:
        """Return as a clean dictionary of categories to skill lists."""
        return {
            "Programming Languages": self.languages,
            "Frameworks & Libraries": self.frameworks,
            "Databases & Storage": self.databases,
            "Developer Tools & Cloud": self.tools,
            "APIs & Protocols": self.apis,
            "Web Technologies": self.web,
            "Other Skills": self.other,
        }

    def to_json(self) -> str:
        """Serialize categorized skills to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ============================================================
# PROJECT DATA
# ============================================================

class ProjectData(BaseModel):
    """A single project extracted and enriched from a resume."""

    id: Optional[int] = None
    title: str = ""
    description: str = ""
    technologies: list[str] = []
    category: str = "General"
    github_url: Optional[str] = None
    live_url: Optional[str] = None


# ============================================================
# RESUME DATA
# ============================================================

class ResumeData(BaseModel):
    """
    Validated, normalized, and enriched resume data.

    All parsers and AI enrichers produce this shape. Pydantic ensures
    type safety, rejects malformed AI output, and handles missing fields gracefully.
    """

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None
    headline: Optional[str] = None

    skills: list[str] = []
    categorized_skills: Optional[CategorizedSkills] = None
    education: list[str] = []
    projects: list[ProjectData] = []
    experience: list[str] = []
    achievements: list[str] = []

    parser_used: str = ""
    ai_provider: str = "none"
    confidence: float = 0.0

    resume_hash: Optional[str] = None
    processing_status: str = "completed"
    last_processed_at: Optional[str] = None


    # --------------------------------------------------------
    # VALIDATORS
    # --------------------------------------------------------

    @field_validator("skills", mode="before")
    @classmethod
    def deduplicate_skills(cls, v):
        """Case-insensitive deduplication of skills."""

        if not isinstance(v, list):
            return v

        seen = set()
        result = []

        for skill in v:

            if not isinstance(skill, str):
                continue

            normalized = skill.strip()

            if not normalized:
                continue

            if normalized.lower() not in seen:
                seen.add(normalized.lower())
                result.append(normalized)

        return result


    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        """Basic email sanity check."""

        if v and "@" not in str(v):
            return None

        if isinstance(v, str):
            return v.strip()

        return v


    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, v):
        """Strip whitespace from name."""

        if isinstance(v, str):
            cleaned = v.strip()
            return cleaned if cleaned else None

        return v


    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    def compute_confidence(self) -> float:
        """
        Estimate parsing and enrichment quality based on how many
        fields were successfully extracted.
        """

        score = 0.0

        if self.name:
            score += 0.20

        if self.email:
            score += 0.15

        if self.summary:
            score += 0.15

        if self.skills:
            score += 0.15

        if self.education:
            score += 0.10

        if self.projects:
            score += 0.15

        if self.experience:
            score += 0.10

        self.confidence = round(score, 2)

        return self.confidence


    # --------------------------------------------------------
    # DATABASE HELPERS
    # --------------------------------------------------------

    def skills_text(self) -> str:
        """Skills as comma-separated string for PostgreSQL."""
        return ", ".join(self.skills)


    def education_text(self) -> str:
        """Education as pipe-separated string for PostgreSQL."""
        return " | ".join(self.education)


    def experience_text(self) -> str:
        """Experience as pipe-separated string for PostgreSQL."""
        return " | ".join(self.experience)


    def achievements_text(self) -> str:
        """Achievements as pipe-separated string for PostgreSQL."""
        return " | ".join(self.achievements)


    def categorized_skills_json(self) -> str:
        """Return categorized skills as JSON string, or empty string."""
        if self.categorized_skills:
            return self.categorized_skills.to_json()
        return ""


# EnrichedResumeData alias for semantic clarity in AI layer
EnrichedResumeData = ResumeData
