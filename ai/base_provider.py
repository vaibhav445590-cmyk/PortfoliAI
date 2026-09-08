"""
PortfoliAI — AI Provider Interface

Abstract base class for all AI and intelligence providers.
Supports operations for resume enrichment, skill categorization,
professional headline derivation, summary polishing, and project classification.

All providers must produce validated Pydantic models.
"""

from abc import ABC, abstractmethod
from typing import Optional
from resume_data import ResumeData, ProjectData, CategorizedSkills


class BaseAIProvider(ABC):
    """
    Abstract interface for AI enrichment providers.

    Implementations can be:
        - Local deterministic/NLP enrichers (always available, free)
        - Local LLM providers (e.g. Ollama, llama.cpp)
        - Cloud AI providers (e.g. OpenAI, Anthropic, Gemini)

    The application must never depend on any single provider and must
    gracefully fall back when an external provider is unavailable or fails.
    """

    @abstractmethod
    def name(self) -> str:
        """Return the unique human-readable provider name."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is currently ready to execute requests.
        Returns True if dependencies, services, or required keys are configured.
        """
        ...

    @abstractmethod
    def enrich_resume(self, resume: ResumeData) -> Optional[ResumeData]:
        """
        Perform comprehensive enrichment on the resume data.
        Returns an enriched ResumeData instance, or None if enrichment fails.
        """
        ...

    @abstractmethod
    def categorize_skills(self, skills: list[str]) -> Optional[CategorizedSkills]:
        """
        Organize a flat list of skills into structured categories:
        Languages, Frameworks, Databases, Tools, APIs, Web Technologies, Other.
        """
        ...

    @abstractmethod
    def generate_headline(self, resume: ResumeData) -> Optional[str]:
        """
        Derive an authentic, professional headline based strictly on education
        and technical strengths present in the resume.
        """
        ...

    @abstractmethod
    def polish_summary(self, resume: ResumeData) -> Optional[str]:
        """
        Polish the professional summary for presentation quality
        without introducing unsupported factual claims.
        """
        ...

    @abstractmethod
    def enrich_projects(self, projects: list[ProjectData]) -> Optional[list[ProjectData]]:
        """
        Classify project categories and refine project descriptions
        while preserving all factual details, technologies, and URLs.
        """
        ...
