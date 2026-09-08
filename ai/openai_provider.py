"""
PortfoliAI — Optional OpenAI Cloud Provider

Optional cloud AI provider.
Only activates if OPENAI_API_KEY is configured in .env.
If the user has zero credits, an expired key, or rate limits,
this provider catches all exceptions and safely returns None,
allowing the system to seamlessly fall back to local intelligence.
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from ai.base_provider import BaseAIProvider
from resume_data import ResumeData, ProjectData, CategorizedSkills


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI API Provider with comprehensive fault tolerance.
    Never crashes the application on missing credits or network errors.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()

    def name(self) -> str:
        return f"OpenAI ({self.model})"

    def is_available(self) -> bool:
        """Check if an API key is configured."""
        return bool(self.api_key and len(self.api_key) > 10)

    def _call_api(self, prompt: str, system: str = "") -> Optional[str]:
        """Safely invoke OpenAI chat completion with fallback on any failure."""
        if not self.is_available():
            return None

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, timeout=10.0)

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2
            )

            if response.choices and response.choices[0].message:
                return response.choices[0].message.content
            return None
        except Exception as e:
            # Cleanly catch quota errors, auth errors, timeouts, etc.
            # Never raise or crash the application.
            print(f"[OpenAIProvider] API call failed ({e.__class__.__name__}). Falling back to local intelligence.")
            return None

    def categorize_skills(self, skills: list[str]) -> Optional[CategorizedSkills]:
        if not self.is_available() or not skills:
            return None

        prompt = f"""
        Categorize the following technical skills:
        {skills}

        Respond ONLY with a JSON object with keys:
        languages, frameworks, databases, tools, apis, web, other
        """
        system = "You are an expert technical resume parser. Return valid JSON only."
        raw = self._call_api(prompt, system)
        if not raw:
            return None

        try:
            data = json.loads(raw)
            return CategorizedSkills(**data)
        except Exception:
            return None

    def generate_headline(self, resume: ResumeData) -> Optional[str]:
        if not self.is_available():
            return None

        prompt = f"""
        Generate a concise professional headline (e.g. 'BCA Student · Backend & API Developer')
        based strictly on:
        Education: {resume.education}
        Skills: {resume.skills[:8]}

        Return JSON: {{"headline": "..."}}
        """
        raw = self._call_api(prompt)
        if not raw:
            return None

        try:
            data = json.loads(raw)
            headline = data.get("headline", "").strip()
            return headline if headline else None
        except Exception:
            return None

    def polish_summary(self, resume: ResumeData) -> Optional[str]:
        if not self.is_available() or not resume.summary:
            return None

        prompt = f"""
        Polish this professional summary without adding any fabricated facts:
        '{resume.summary}'

        Return JSON: {{"summary": "..."}}
        """
        raw = self._call_api(prompt)
        if not raw:
            return None

        try:
            data = json.loads(raw)
            summary = data.get("summary", "").strip()
            return summary if summary else None
        except Exception:
            return None

    def enrich_projects(self, projects: list[ProjectData]) -> Optional[list[ProjectData]]:
        return None  # Prefer deterministic local categorization for projects

    def enrich_resume(self, resume: ResumeData) -> Optional[ResumeData]:
        if not self.is_available():
            return None

        headline = self.generate_headline(resume)
        summary = self.polish_summary(resume)
        categorized_skills = self.categorize_skills(resume.skills)

        # If all calls failed (e.g. no credits), return None to trigger fallback
        if not headline and not summary and not categorized_skills:
            return None

        enriched = ResumeData(
            name=resume.name,
            email=resume.email,
            phone=resume.phone,
            summary=summary or resume.summary,
            headline=headline,
            skills=resume.skills,
            categorized_skills=categorized_skills,
            education=resume.education,
            projects=resume.projects,
            experience=resume.experience,
            achievements=resume.achievements,
            parser_used=resume.parser_used,
            ai_provider=self.name(),
            confidence=resume.confidence,
            processing_status="completed"
        )
        enriched.compute_confidence()
        return enriched
