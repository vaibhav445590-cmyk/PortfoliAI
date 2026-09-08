"""
PortfoliAI — Ollama Local LLM Provider

Free, local LLM integration using Ollama (http://localhost:11434).
Runs entirely offline without cloud APIs or credit consumption.
If Ollama is not installed or not running, is_available() returns False
and calls fail gracefully, causing the pipeline to fall back to LocalEnricher.
"""

import json
import urllib.request
import urllib.error
from typing import Optional
from ai.base_provider import BaseAIProvider
from resume_data import ResumeData, ProjectData, CategorizedSkills


class OllamaProvider(BaseAIProvider):
    """
    Ollama local model provider.
    Connects to local Ollama daemon if available.
    """

    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3.2"):
        self.host = host.rstrip("/")
        self.model = model

    def name(self) -> str:
        return f"Ollama ({self.model})"

    def is_available(self) -> bool:
        """Ping local Ollama daemon to check if it's running."""
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                headers={"User-Agent": "PortfoliAI"}
            )
            with urllib.request.urlopen(req, timeout=0.8) as response:
                return response.status == 200
        except Exception:
            return False

    def _generate(self, prompt: str, system: str = "") -> Optional[str]:
        """Send a prompt to Ollama /api/generate endpoint."""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "format": "json"
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "PortfoliAI"}
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status == 200:
                    res_json = json.loads(response.read().decode("utf-8"))
                    return res_json.get("response")
            return None
        except Exception:
            return None

    def categorize_skills(self, skills: list[str]) -> Optional[CategorizedSkills]:
        """Ask Ollama to categorize skills into JSON."""
        if not self.is_available() or not skills:
            return None

        prompt = f"""
        Categorize the following technical skills into JSON categories:
        Skills: {skills}

        Respond ONLY with a JSON object with these exact keys:
        {{
            "languages": [],
            "frameworks": [],
            "databases": [],
            "tools": [],
            "apis": [],
            "web": [],
            "other": []
        }}
        """
        response = self._generate(prompt)
        if not response:
            return None

        try:
            data = json.loads(response)
            return CategorizedSkills(**data)
        except Exception:
            return None

    def generate_headline(self, resume: ResumeData) -> Optional[str]:
        if not self.is_available():
            return None

        prompt = f"""
        Generate a single concise professional headline (e.g. 'BCA Student · Backend & API Developer')
        based on:
        Education: {resume.education}
        Skills: {resume.skills[:8]}

        Respond with JSON: {{"headline": "..."}}
        """
        response = self._generate(prompt)
        if not response:
            return None

        try:
            data = json.loads(response)
            headline = data.get("headline", "").strip()
            return headline if headline else None
        except Exception:
            return None

    def polish_summary(self, resume: ResumeData) -> Optional[str]:
        if not self.is_available() or not resume.summary:
            return None

        prompt = f"""
        Polish this professional resume summary for presentation. Keep it truthful to the text:
        '{resume.summary}'

        Respond with JSON: {{"summary": "..."}}
        """
        response = self._generate(prompt)
        if not response:
            return None

        try:
            data = json.loads(response)
            summary = data.get("summary", "").strip()
            return summary if summary else None
        except Exception:
            return None

    def enrich_projects(self, projects: list[ProjectData]) -> Optional[list[ProjectData]]:
        return None  # Let local enricher handle project categorization deterministically

    def enrich_resume(self, resume: ResumeData) -> Optional[ResumeData]:
        if not self.is_available():
            return None

        headline = self.generate_headline(resume)
        summary = self.polish_summary(resume)
        categorized_skills = self.categorize_skills(resume.skills)

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
