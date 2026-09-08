"""
PortfoliAI — Enhanced Regex Resume Parser

Improved version of the original regex-based parser.
Implements BaseResumeParser so it works with the pipeline.

Improvements over the original resume_parser.py:
    - Fuzzy section header matching (substring/contains)
    - Better name detection heuristics
    - Technology extraction from project descriptions
    - URL extraction (GitHub, LinkedIn)
    - Case-insensitive skill deduplication (via Pydantic)
    - Produces validated ResumeData instead of raw dict

This parser has ZERO external dependencies beyond stdlib
and Pydantic, and always returns a result (never None).
It is the guaranteed fallback in the pipeline.
"""

import re
import sys
import os

# Allow imports from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from parser_base import BaseResumeParser
from resume_data import ResumeData, ProjectData


# ============================================================
# KNOWN TECHNOLOGIES
# ============================================================

KNOWN_TECHNOLOGIES = {
    # Languages
    "python", "java", "javascript", "typescript", "c",
    "c++", "c#", "ruby", "go", "rust", "php", "swift",
    "kotlin", "dart", "r", "scala", "perl", "lua",
    "matlab", "bash", "shell",

    # Web
    "html", "css", "sass", "scss", "less", "tailwind",
    "bootstrap", "react", "angular", "vue", "svelte",
    "next.js", "nuxt", "gatsby", "jquery",

    # Backend
    "node.js", "express", "flask", "django", "fastapi",
    "spring", "spring boot", "rails", "laravel", "asp.net",

    # Database
    "sql", "mysql", "postgresql", "postgres", "mongodb",
    "sqlite", "redis", "firebase", "supabase", "dynamodb",
    "cassandra", "oracle",

    # AI / ML
    "tensorflow", "pytorch", "keras", "scikit-learn",
    "pandas", "numpy", "opencv", "nltk", "spacy",
    "hugging face", "transformers", "langchain",
    "openai", "gpt", "llm", "machine learning",
    "deep learning", "nlp", "computer vision",

    # DevOps / Cloud
    "docker", "kubernetes", "aws", "azure", "gcp",
    "heroku", "vercel", "netlify", "linux", "nginx",
    "apache", "ci/cd", "jenkins", "github actions",

    # Tools
    "git", "github", "gitlab", "bitbucket", "jira",
    "figma", "postman", "vscode", "vim",

    # APIs / Protocols
    "rest", "rest api", "rest apis", "graphql",
    "websocket", "grpc",

    # Mobile
    "android", "ios", "react native", "flutter",
    "swiftui", "jetpack compose",

    # Other
    "agile", "scrum", "oop", "data structures",
    "algorithms", "api", "microservices",
}


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    """Collapse whitespace and strip."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_urls(text):
    """Extract GitHub and LinkedIn URLs from text."""

    urls = {
        "github": None,
        "linkedin": None,
        "portfolio": None,
    }

    github_match = re.search(
        r"https?://(?:www\.)?github\.com/[\w\-]+",
        text,
        re.IGNORECASE
    )

    if github_match:
        urls["github"] = github_match.group(0)

    linkedin_match = re.search(
        r"https?://(?:www\.)?linkedin\.com/in/[\w\-]+",
        text,
        re.IGNORECASE
    )

    if linkedin_match:
        urls["linkedin"] = linkedin_match.group(0)

    return urls


def extract_technologies_from_text(text):
    """
    Find known technologies mentioned in a text block.
    Used to populate project technologies when not
    explicitly listed.
    """

    found = []
    text_lower = text.lower()

    for tech in KNOWN_TECHNOLOGIES:

        # Word-boundary match to avoid partial matches
        pattern = r"\b" + re.escape(tech) + r"\b"

        if re.search(pattern, text_lower):

            # Use the canonical casing from the set
            # (capitalize first letter for display)
            found.append(tech.title() if len(tech) > 3 else tech.upper())

    # Deduplicate while preserving order
    seen = set()
    result = []

    for t in found:
        if t.lower() not in seen:
            seen.add(t.lower())
            result.append(t)

    return result


# ============================================================
# SECTION HEADER MATCHING
# ============================================================

SECTION_PATTERNS = {
    "summary": [
        "summary", "profile", "about me", "about",
        "objective", "career objective",
        "professional summary", "personal statement",
    ],

    "skills": [
        "skills", "technical skills", "technologies",
        "technical expertise", "core competencies",
        "competencies", "tools", "tools and technologies",
        "skills and tools", "technical skills and tools",
        "programming languages", "frameworks",
        "tech stack",
    ],

    "education": [
        "education", "academic background",
        "academic qualifications", "qualifications",
        "educational background", "academics",
    ],

    "projects": [
        "projects", "personal projects",
        "academic projects", "key projects",
        "selected projects", "notable projects",
        "side projects", "project work",
    ],

    "experience": [
        "experience", "work experience",
        "professional experience", "internship",
        "internships", "employment", "work history",
        "employment history",
    ],

    "achievements": [
        "achievements", "certifications",
        "certification", "awards", "honors",
        "accomplishments", "courses",
        "certificates", "licenses",
    ],
}


def match_section_header(normalized_line):
    """
    Match a normalized line against known section headers.

    Uses two strategies:
        1. Exact match (original behavior)
        2. Substring/contains match (new — catches
           "TECHNICAL SKILLS & TOOLS" etc.)

    Returns the section key or None.
    """

    # Strategy 1: exact match
    for section, names in SECTION_PATTERNS.items():

        if normalized_line in names:
            return section

    # Strategy 2: substring match
    # Check if any known name is contained in the line,
    # but ONLY if the line looks like a section header:
    #   - Short (< 50 chars)
    #   - No sentence-ending punctuation (period, comma)
    #   - Few words (<= 6)
    # This prevents matching "experience" inside
    # "5 years of experience."

    words = normalized_line.split()

    is_header_like = (
        len(normalized_line) < 50
        and "." not in normalized_line
        and "," not in normalized_line
        and len(words) <= 6
    )

    if is_header_like:

        for section, names in SECTION_PATTERNS.items():

            for name in names:

                if name in normalized_line:
                    return section

    return None


# ============================================================
# ENHANCED REGEX PARSER
# ============================================================

class EnhancedRegexParser(BaseResumeParser):
    """
    Enhanced regex-based resume parser.

    Always available. Zero external dependencies.
    Guaranteed fallback in the pipeline.
    """


    def name(self) -> str:
        return "Enhanced Regex"


    def is_available(self) -> bool:
        return True


    def parse(self, text: str) -> ResumeData | None:
        """
        Parse resume text into validated ResumeData.

        This method never returns None — it always
        produces at least a partial result.
        """

        if not text or not text.strip():
            return ResumeData(parser_used=self.name())

        # --------------------------------------------------
        # CLEAN LINES
        # --------------------------------------------------

        lines = [
            clean_text(line)
            for line in text.splitlines()
            if clean_text(line)
        ]

        if not lines:
            return ResumeData(parser_used=self.name())


        # --------------------------------------------------
        # EMAIL
        # --------------------------------------------------

        email = None

        email_match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text
        )

        if email_match:
            email = email_match.group(0)


        # --------------------------------------------------
        # PHONE
        # --------------------------------------------------

        phone = None

        phone_patterns = [
            r"(?:\+91[\s-]?)?[6-9]\d{9}",
            r"(?:\+91[\s-]?)?\d{10}",
            r"(?:\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
        ]

        for pattern in phone_patterns:

            phone_match = re.search(pattern, text)

            if phone_match:
                phone = phone_match.group(0)
                break


        # --------------------------------------------------
        # URLS
        # --------------------------------------------------

        urls = extract_urls(text)


        # --------------------------------------------------
        # NAME
        # --------------------------------------------------

        name = None

        for line in lines[:5]:

            lower = line.lower()

            # Skip lines that are clearly not a name
            if (
                "resume" in lower
                or "curriculum vitae" in lower
                or "cv" == lower
                or "email" in lower
                or "phone" in lower
                or "address" in lower
                or "contact" in lower
                or "@" in line
                or not re.search(r"[A-Za-z]", line)
                or re.search(r"\d{5,}", line)
            ):
                continue

            # Additional heuristics:
            # A name line is typically short (< 50 chars)
            # and mostly alphabetic words
            words = line.split()

            if (
                len(words) <= 5
                and len(line) < 50
                and all(
                    re.match(r"^[A-Za-z.\-']+$", w)
                    for w in words
                )
            ):
                name = line
                break

        # Fallback: if strict heuristic found nothing,
        # use the original looser strategy
        if not name:

            for line in lines[:5]:

                lower = line.lower()

                if (
                    "resume" not in lower
                    and "curriculum vitae" not in lower
                    and "email" not in lower
                    and "phone" not in lower
                    and "@" not in line
                    and not re.search(r"\d{5,}", line)
                ):
                    name = line
                    break


        # --------------------------------------------------
        # SECTION DETECTION (with fuzzy matching)
        # --------------------------------------------------

        sections = {}
        current_section = None

        for line in lines:

            detected_section = None
            remainder = None

            # First check if line has inline section header e.g. "Education: BCA 2026" or "Skills: Python, React"
            if ":" in line:
                prefix, rest = line.split(":", 1)
                norm_prefix = prefix.lower().strip(" :-–—")
                sec = match_section_header(norm_prefix)
                if sec:
                    detected_section = sec
                    if rest.strip():
                        remainder = rest.strip()

            if not detected_section:
                normalized = line.lower().strip(" :-–—")
                detected_section = match_section_header(
                    normalized
                )

            if detected_section:
                current_section = detected_section
                if current_section not in sections:
                    sections[current_section] = []
                if remainder:
                    sections[current_section].append(remainder)
                continue

            if current_section:
                sections[current_section].append(line)


        # --------------------------------------------------
        # SUMMARY
        # --------------------------------------------------

        summary = None

        if sections.get("summary"):
            summary = " ".join(sections["summary"])


        # --------------------------------------------------
        # SKILLS
        # --------------------------------------------------

        skills = []

        if sections.get("skills"):

            skill_text = " ".join(sections["skills"])

            raw_skills = re.split(
                r"[,|•;/]",
                skill_text
            )

            for skill in raw_skills:

                skill = skill.strip(" ·-–—•")

                if skill:
                    skills.append(skill)


        # --------------------------------------------------
        # EDUCATION
        # --------------------------------------------------

        education = []

        if sections.get("education"):
            education = sections["education"]


        # --------------------------------------------------
        # PROJECTS
        # --------------------------------------------------

        projects = []

        if sections.get("projects"):

            project_lines = sections["projects"]

            current_project = None

            for line in project_lines:

                # Detect title — description separator
                if (
                    "—" in line
                    or "–" in line
                    or ":" in line
                ):

                    parts = re.split(
                        r"\s*[—–:]\s*",
                        line,
                        maxsplit=1
                    )

                    if len(parts) == 2:

                        title = parts[0].strip()
                        description = parts[1].strip()

                        # Extract technologies from the
                        # combined title + description
                        techs = extract_technologies_from_text(
                            f"{title} {description}"
                        )

                        projects.append(
                            ProjectData(
                                title=title,
                                description=description,
                                technologies=techs,
                            )
                        )

                        current_project = projects[-1]

                        continue

                # No separator: first line is title
                if current_project is None:

                    techs = extract_technologies_from_text(
                        line
                    )

                    projects.append(
                        ProjectData(
                            title=line,
                            description="",
                            technologies=techs,
                        )
                    )

                    current_project = projects[-1]

                else:

                    # Continuation line → append to
                    # previous project's description
                    if current_project.description:
                        current_project.description += " " + line
                    else:
                        current_project.description = line

                    # Re-extract technologies with the
                    # now-complete description
                    combined = (
                        f"{current_project.title} "
                        f"{current_project.description}"
                    )

                    current_project.technologies = (
                        extract_technologies_from_text(
                            combined
                        )
                    )

            # Extract URLs for each project from its description and title
            for project in projects:
                combined_proj_text = f"{project.title} {project.description}"

                # Check for GitHub repository URL
                gh_match = re.search(
                    r"https?://(?:www\.)?github\.com/[\w\-]+(?:/[\w\-]+)?",
                    combined_proj_text,
                    re.IGNORECASE
                )
                if gh_match and not project.github_url:
                    project.github_url = gh_match.group(0)

                # Check for Live / Demo URL (not GitHub or LinkedIn)
                url_matches = re.findall(
                    r"https?://[^\s,;()]+",
                    combined_proj_text,
                    re.IGNORECASE
                )
                for u in url_matches:
                    u_clean = u.rstrip(".,;)")
                    u_lower = u_clean.lower()
                    if "github.com" not in u_lower and "linkedin.com" not in u_lower:
                        if not project.live_url:
                            project.live_url = u_clean
                            break

            # Fallback: If only 1 project and 1 GitHub URL found in entire project section
            project_text = " ".join(project_lines)
            github_urls = re.findall(
                r"https?://(?:www\.)?github\.com/[\w\-]+/[\w\-]+",
                project_text,
                re.IGNORECASE
            )
            if len(projects) == 1 and len(github_urls) == 1 and not projects[0].github_url:
                projects[0].github_url = github_urls[0]


        # --------------------------------------------------
        # EXPERIENCE
        # --------------------------------------------------

        experience = []

        if sections.get("experience"):
            experience = sections["experience"]


        # --------------------------------------------------
        # ACHIEVEMENTS
        # --------------------------------------------------

        achievements = []

        if sections.get("achievements"):
            achievements = sections["achievements"]


        # --------------------------------------------------
        # BUILD VALIDATED RESULT
        # --------------------------------------------------

        result = ResumeData(
            name=name,
            email=email,
            phone=phone,
            summary=summary,
            skills=skills,
            education=education,
            projects=projects,
            experience=experience,
            achievements=achievements,
            parser_used=self.name(),
        )

        result.compute_confidence()

        return result
