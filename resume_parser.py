import re


def clean_text(text):
    """Clean unnecessary spaces and characters."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_resume_text(text):
    """
    Convert extracted resume text into structured data.
    """

    data = {
        "name": None,
        "email": None,
        "phone": None,
        "summary": None,
        "skills": [],
        "education": [],
        "projects": [],
        "experience": [],
        "achievements": []
    }

    # --------------------------------------------------
    # CLEAN TEXT
    # --------------------------------------------------

    lines = [
        clean_text(line)
        for line in text.splitlines()
        if clean_text(line)
    ]

    # --------------------------------------------------
    # EMAIL
    # --------------------------------------------------

    email_match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    if email_match:
        data["email"] = email_match.group(0)

    # --------------------------------------------------
    # PHONE
    # --------------------------------------------------

    phone_patterns = [
        r"(?:\+91[\s-]?)?[6-9]\d{9}",
        r"(?:\+91[\s-]?)?\d{10}"
    ]

    for pattern in phone_patterns:
        phone_match = re.search(pattern, text)

        if phone_match:
            data["phone"] = phone_match.group(0)
            break

    # --------------------------------------------------
    # NAME
    # --------------------------------------------------

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
            data["name"] = line
            break

    # --------------------------------------------------
    # SECTION DETECTION
    # --------------------------------------------------

    section_patterns = {
        "summary": [
            "summary",
            "profile",
            "about me",
            "objective"
        ],

        "skills": [
            "skills",
            "technical skills",
            "technical skills:",
            "technologies",
            "technical expertise"
        ],

        "education": [
            "education",
            "education:",
            "academic background"
        ],

        "projects": [
            "projects",
            "projects:",
            "personal projects",
            "academic projects"
        ],

        "experience": [
            "experience",
            "experience:",
            "work experience",
            "internship",
            "internships"
        ],

        "achievements": [
            "achievements",
            "achievements:",
            "certifications",
            "certification",
            "awards"
        ]
    }

    sections = {}
    current_section = None

    for line in lines:

        normalized = line.lower().strip(" :-")

        detected_section = None

        for section, names in section_patterns.items():

            if normalized in names:
                detected_section = section
                break

        if detected_section:

            current_section = detected_section
            sections[current_section] = []

            continue

        if current_section:
            sections[current_section].append(line)

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    if sections.get("summary"):

        summary_lines = sections["summary"]

        data["summary"] = " ".join(summary_lines)

    # --------------------------------------------------
    # SKILLS
    # --------------------------------------------------

    if sections.get("skills"):

        skill_text = " ".join(sections["skills"])

        skills = re.split(
            r"[,|•;]",
            skill_text
        )

        cleaned_skills = []

        for skill in skills:

            skill = skill.strip()

            if skill and skill not in cleaned_skills:
                cleaned_skills.append(skill)

        data["skills"] = cleaned_skills

    # --------------------------------------------------
    # EDUCATION
    # --------------------------------------------------

    if sections.get("education"):

        education_lines = sections["education"]

        data["education"] = education_lines

    # --------------------------------------------------
    # PROJECTS
    # --------------------------------------------------

    if sections.get("projects"):

        project_lines = sections["projects"]

        projects = []

        current_project = None

        for line in project_lines:

            # Detect common project title formats
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

                    projects.append({
                        "title": title,
                        "description": description
                    })

                    current_project = projects[-1]

                    continue

            # If no title/description separator exists,
            # treat the first line as the title.
            if current_project is None:

                projects.append({
                    "title": line,
                    "description": ""
                })

                current_project = projects[-1]

            else:

                # Wrapped PDF lines belong to
                # the previous project's description.
                if current_project["description"]:

                    current_project["description"] += " " + line

                else:

                    current_project["description"] = line

        data["projects"] = projects

    # --------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------

    if sections.get("experience"):

        data["experience"] = sections["experience"]

    # --------------------------------------------------
    # ACHIEVEMENTS
    # --------------------------------------------------

    if sections.get("achievements"):

        data["achievements"] = sections["achievements"]

    return data