"""
PortfoliAI — AI Enrichment Orchestration Service

Orchestrates the AI enrichment layer with automatic fallback:
    1. Tries configured LLM providers (Ollama, OpenAI) if available
    2. Gracefully falls back to LocalEnricher on ANY error (no credits, timeout, network error)
    3. Validates all enriched data against Pydantic models
    4. Enforces strict anti-hallucination guardrails:
       - No invented URLs
       - Preserves all original skills and experiences
    5. Computes resume content hash for intelligent caching and status tracking
"""

import hashlib
from datetime import datetime, timezone
from typing import Optional
from ai.base_provider import BaseAIProvider
from ai.local_enricher import LocalEnricher
from resume_data import ResumeData, ProjectData, CategorizedSkills


class EnrichmentService:
    """
    Enrichment service managing provider priority and fallback.
    Guarantees that enrichment never crashes and always returns valid data.
    """

    def __init__(self):
        self._providers: list[BaseAIProvider] = []
        self._local_fallback = LocalEnricher()

    def register(self, provider: BaseAIProvider):
        """Add a provider to the enrichment chain."""
        self._providers.append(provider)

    @property
    def providers(self) -> list[BaseAIProvider]:
        return list(self._providers)

    @staticmethod
    def compute_resume_hash(text: str) -> str:
        """Compute SHA256 digest of resume text for change detection and caching."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _sanitize_and_merge(
        self,
        original: ResumeData,
        candidate: Optional[ResumeData],
        provider_name: str
    ) -> ResumeData:
        """
        Merge candidate enriched data with original parsed data.
        Enforces anti-hallucination guardrails:
        - Never replaces non-empty fields with empty values.
        - Preserves all original skills and projects.
        - If candidate is None or incomplete, uses local enricher.
        """
        local_result = self._local_fallback.enrich_resume(original)

        if not candidate:
            candidate = local_result
            provider_name = self._local_fallback.name()

        # 1. Headline
        headline = candidate.headline or local_result.headline

        # 2. Summary
        summary = candidate.summary or local_result.summary or original.summary

        # 3. Categorized skills
        categorized_skills = candidate.categorized_skills or local_result.categorized_skills
        # Guardrail: ensure all original skills are present
        if categorized_skills:
            present_skills = {s.lower() for s in categorized_skills.all_skills()}
            for skill in original.skills:
                if skill.lower() not in present_skills:
                    categorized_skills.other.append(skill)
                    present_skills.add(skill.lower())

        # 4. Enriched projects
        # Project classification from candidate or local fallback
        merged_projects = []
        local_projects_map = {p.title.lower(): p for p in local_result.projects}

        for p in original.projects:
            loc = local_projects_map.get(p.title.lower(), p)
            # Find in candidate
            cand = next((cp for cp in (candidate.projects or []) if cp.title.lower() == p.title.lower()), None)

            category = (cand.category if cand and cand.category != "General" else loc.category)
            description = (cand.description if cand and cand.description else (loc.description or p.description))

            merged_projects.append(ProjectData(
                title=p.title,
                description=description,
                technologies=p.technologies,
                category=category,
                github_url=p.github_url,
                live_url=p.live_url
            ))

        now_str = datetime.now(timezone.utc).isoformat()

        enriched = ResumeData(
            name=original.name,
            email=original.email,
            phone=original.phone,
            summary=summary,
            headline=headline,
            skills=original.skills,
            categorized_skills=categorized_skills,
            education=original.education,
            projects=merged_projects,
            experience=original.experience,
            achievements=original.achievements,
            parser_used=original.parser_used,
            ai_provider=provider_name,
            confidence=original.confidence,
            processing_status="completed",
            last_processed_at=now_str
        )
        enriched.compute_confidence()
        return enriched

    def enrich(self, resume: ResumeData, resume_text: Optional[str] = None) -> ResumeData:
        """
        Execute the enrichment pipeline across available providers with safe fallback.
        """
        if resume_text:
            resume.resume_hash = self.compute_resume_hash(resume_text)

        # Try providers in priority order
        for provider in self._providers:
            try:
                if not provider.is_available():
                    continue

                print(f"[EnrichmentService] Attempting enrichment with: {provider.name()}")
                candidate = provider.enrich_resume(resume)
                if candidate:
                    print(f"[EnrichmentService] Successfully enriched using: {provider.name()}")
                    enriched = self._sanitize_and_merge(resume, candidate, provider.name())
                    if resume.resume_hash:
                        enriched.resume_hash = resume.resume_hash
                    return enriched
            except Exception as e:
                print(f"[EnrichmentService] Provider {provider.name()} failed ({e}). Falling back.")
                continue

        # Final guaranteed fallback: Local Intelligence
        print(f"[EnrichmentService] Using guaranteed fallback: {self._local_fallback.name()}")
        enriched = self._sanitize_and_merge(resume, None, self._local_fallback.name())
        if resume.resume_hash:
            enriched.resume_hash = resume.resume_hash
        return enriched


def create_default_enrichment_service() -> EnrichmentService:
    """
    Factory creating standard enrichment pipeline:
        1. Ollama (Local free LLM, if running)
        2. OpenAI (Cloud LLM, if configured and has credits)
        3. Local Intelligence (Deterministic, always available, zero-cost fallback)
    """
    from ai.ollama_provider import OllamaProvider
    from ai.openai_provider import OpenAIProvider

    service = EnrichmentService()
    service.register(OllamaProvider())
    service.register(OpenAIProvider())
    service.register(LocalEnricher())
    return service
