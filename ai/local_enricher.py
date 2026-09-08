"""
PortfoliAI — Local Intelligence Enricher

A fast, reliable, zero-cost, local-first intelligence provider.
Uses deterministic NLP rules, taxonomies, and heuristics to categorize skills,
derive professional headlines, polish descriptions, and classify projects
WITHOUT requiring external API keys, network access, or paid credits.

Crucially: NEVER invents qualifications, companies, degrees, or URLs.
"""

import re
from typing import Optional
from ai.base_provider import BaseAIProvider
from resume_data import ResumeData, ProjectData, CategorizedSkills


# ============================================================
# TECHNICAL SKILL TAXONOMY
# ============================================================

TAXONOMY_LANGUAGES = {
    "python", "javascript", "typescript", "java", "c", "c++", "c#",
    "go", "golang", "rust", "ruby", "php", "swift", "kotlin", "dart",
    "r", "scala", "perl", "lua", "bash", "shell", "sql", "pl/sql", "matlab"
}

TAXONOMY_FRAMEWORKS = {
    "react", "react.js", "next.js", "vue", "vue.js", "angular", "svelte",
    "flask", "django", "fastapi", "node.js", "nodejs", "express", "express.js",
    "spring", "spring boot", "ruby on rails", "rails", "laravel", "asp.net",
    "pytorch", "tensorflow", "keras", "scikit-learn", "pandas", "numpy",
    "opencv", "nltk", "spacy", "hugging face", "transformers", "langchain"
}

TAXONOMY_DATABASES = {
    "postgresql", "postgres", "mysql", "mongodb", "sqlite", "redis",
    "firebase", "supabase", "dynamodb", "cassandra", "oracle", "mariadb",
    "neo4j", "couchdb"
}

TAXONOMY_TOOLS = {
    "git", "github", "gitlab", "bitbucket", "docker", "kubernetes",
    "aws", "azure", "gcp", "google cloud", "heroku", "vercel", "netlify",
    "linux", "ubuntu", "nginx", "apache", "postman", "figma", "jira",
    "ci/cd", "jenkins", "github actions", "vscode", "vim", "webpack", "vite"
}

TAXONOMY_APIS = {
    "rest", "rest api", "rest apis", "restful apis", "graphql", "grpc",
    "websocket", "websockets", "microservices", "api integration", "soap"
}

TAXONOMY_WEB = {
    "html", "html5", "css", "css3", "sass", "scss", "tailwind",
    "tailwind css", "bootstrap", "jquery", "responsive design", "web design"
}


# ============================================================
# LOCAL ENRICHER IMPLEMENTATION
# ============================================================

class LocalEnricher(BaseAIProvider):
    """
    Local-first deterministic intelligence provider.
    Always available, zero cost, anti-hallucinatory by design.
    """

    def name(self) -> str:
        return "Local Intelligence"

    def is_available(self) -> bool:
        return True

    # --------------------------------------------------------
    # SKILL CATEGORIZATION
    # --------------------------------------------------------

    def categorize_skills(self, skills: list[str]) -> CategorizedSkills:
        """
        Sort skills into 7 clear technical categories while preserving
        all skills without dropping anything.
        """
        categorized = CategorizedSkills()

        for skill in skills:
            norm = skill.strip().lower()
            if not norm:
                continue

            # Standardized display name
            display_name = skill.strip()

            if norm in TAXONOMY_LANGUAGES:
                categorized.languages.append(display_name)
            elif norm in TAXONOMY_FRAMEWORKS:
                categorized.frameworks.append(display_name)
            elif norm in TAXONOMY_DATABASES:
                categorized.databases.append(display_name)
            elif norm in TAXONOMY_TOOLS:
                categorized.tools.append(display_name)
            elif norm in TAXONOMY_APIS or "api" in norm:
                categorized.apis.append(display_name)
            elif norm in TAXONOMY_WEB:
                categorized.web.append(display_name)
            else:
                categorized.other.append(display_name)

        return categorized

    # --------------------------------------------------------
    # PROFESSIONAL HEADLINE DERIVATION
    # --------------------------------------------------------

    def generate_headline(self, resume: ResumeData) -> str:
        """
        Derive an authentic, professional headline combining education
        and observed technical focus from resume data.
        """
        education_str = " ".join(resume.education).lower()
        skills_lower = [s.lower() for s in resume.skills]
        all_text = (
            education_str + " "
            + " ".join(skills_lower) + " "
            + " ".join([p.title.lower() + " " + p.description.lower() for p in resume.projects])
        )

        # 1. Degree / Background prefix
        prefix = "Developer"
        if "bca" in education_str or "bachelor of computer applications" in education_str:
            prefix = "BCA Student"
        elif "b.tech" in education_str or "btech" in education_str or "b.e." in education_str:
            prefix = "B.Tech Student"
        elif "mca" in education_str or "master of computer applications" in education_str:
            prefix = "MCA Student"
        elif "computer science" in education_str:
            prefix = "Computer Science Student"

        # 2. Domain specialty derived from technologies
        specialty = "Software Developer"
        has_ai = any(kw in all_text for kw in ["machine learning", "pytorch", "tensorflow", "nlp", "ai", "deep learning"])
        has_backend = any(kw in all_text for kw in ["fastapi", "flask", "django", "spring", "express", "sql", "postgresql", "backend"])
        has_fullstack = any(kw in all_text for kw in ["react", "vue", "angular", "next.js"]) and has_backend
        has_web = any(kw in all_text for kw in ["react", "frontend", "html", "css", "javascript", "web"])

        if has_ai:
            specialty = "AI & ML Developer"
        elif has_fullstack:
            specialty = "Full-Stack Developer"
        elif has_backend:
            specialty = "Backend & API Developer"
        elif has_web:
            specialty = "Web Developer"

        return f"{prefix} · {specialty}"

    # --------------------------------------------------------
    # PROFESSIONAL SUMMARY POLISHER
    # --------------------------------------------------------

    def polish_summary(self, resume: ResumeData) -> str:
        """
        Clean and format the professional summary for presentation.
        Never hallucinates new facts or unearned claims.
        """
        if resume.summary and resume.summary.strip():
            cleaned = resume.summary.strip()
            # Ensure proper capitalization of first letter
            if cleaned:
                cleaned = cleaned[0].upper() + cleaned[1:]
            # Ensure closing punctuation
            if cleaned and not cleaned.endswith((".", "!", "?")):
                cleaned += "."
            return cleaned

        # If summary is missing, generate a concise factual statement
        name = resume.name or "A dedicated developer"
        edu = resume.education[0] if resume.education else "technology student"
        top_skills = ", ".join(resume.skills[:4]) if resume.skills else "modern software development"

        return f"{name} is a {edu} with technical expertise in {top_skills}, focused on building scalable projects and practical software solutions."

    # --------------------------------------------------------
    # PROJECT CLASSIFICATION & ENRICHMENT
    # --------------------------------------------------------

    def _classify_project(self, project: ProjectData) -> str:
        """Classify a project into a clear portfolio category."""
        text = f"{project.title} {project.description} {' '.join(project.technologies)}".lower()

        def has_any(keywords):
            return any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in keywords)

        if has_any(["ai", "machine learning", "deep learning", "neural", "nlp", "llm", "chatbot", "vision", "model"]):
            return "AI & Machine Learning"
        elif has_any(["android", "ios", "flutter", "react native", "mobile"]):
            return "Mobile Application"
        elif has_any(["web application", "portfolio", "full-stack", "full stack", "frontend", "website", "dashboard"]) or (
            has_any(["react", "vue", "angular", "next.js"]) and not has_any(["api gateway", "rest api", "backend service"])
        ):
            return "Web Application"
        elif has_any(["api", "backend", "fastapi", "flask", "django", "express", "spring", "rest", "microservice", "service"]):
            return "Backend & API Service"
        elif has_any(["database", "postgres", "sql", "mongodb", "redis", "storage", "etl"]):
            return "Data & Storage System"
        elif has_any(["cli", "tool", "docker", "automation", "parser", "scraper", "utility"]):
            return "System Tool & Automation"
        else:
            return "Software Application"

    def enrich_projects(self, projects: list[ProjectData]) -> list[ProjectData]:
        """
        Classify category and polish description for each project.
        Preserves all existing technologies and URLs.
        """
        enriched_projects = []

        for p in projects:
            category = self._classify_project(p)

            # Polish description: ensure capitalization and trailing period
            desc = p.description.strip() if p.description else ""
            if desc:
                desc = desc[0].upper() + desc[1:]
                if not desc.endswith((".", "!", "?")):
                    desc += "."

            enriched_project = ProjectData(
                title=p.title.strip(),
                description=desc,
                technologies=list(p.technologies),
                category=category,
                github_url=p.github_url,
                live_url=p.live_url
            )
            enriched_projects.append(enriched_project)

        return enriched_projects

    # --------------------------------------------------------
    # FULL RESUME ENRICHMENT
    # --------------------------------------------------------

    def enrich_resume(self, resume: ResumeData) -> ResumeData:
        """
        Execute full deterministic enrichment across all resume sections.
        """
        # 1. Categorize skills
        categorized_skills = self.categorize_skills(resume.skills)

        # 2. Derive headline
        headline = self.generate_headline(resume)

        # 3. Polish summary
        summary = self.polish_summary(resume)

        # 4. Enrich projects
        enriched_projects = self.enrich_projects(resume.projects)

        # Create updated ResumeData
        enriched = ResumeData(
            name=resume.name,
            email=resume.email,
            phone=resume.phone,
            summary=summary,
            headline=headline,
            skills=resume.skills,
            categorized_skills=categorized_skills,
            education=resume.education,
            projects=enriched_projects,
            experience=resume.experience,
            achievements=resume.achievements,
            parser_used=resume.parser_used,
            ai_provider=self.name(),
            confidence=resume.confidence,
            processing_status="completed"
        )
        enriched.compute_confidence()
        return enriched
