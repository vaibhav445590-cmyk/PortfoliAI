"""
PortfoliAI — Phase 1 Hardening Tests

Comprehensive tests covering:
    1. Experience storage
    2. Achievements storage
    3. Project technologies, github_url, live_url
    4. Parser metadata (parser_used)
    5. Data safety (COALESCE protection)
    6. Migration behavior (column existence)
    7. ResumeData validation edge cases
    8. Full pipeline round-trip
"""

import sys
sys.path.insert(0, ".")

from parser_pipeline import create_default_pipeline
from resume_data import ResumeData, ProjectData


pipeline = create_default_pipeline()

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed

    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")
        if detail:
            print(f"        {detail}")


# ============================================================
# FULL RESUME WITH ALL SECTIONS
# ============================================================

full_resume = """
Priya Mehta
Email: priya.mehta@university.edu
Phone: +91 9876543210

Summary
Computer Science student passionate about web development,
cloud computing, and open source contributions.

Technical Skills
Python, JavaScript, React, Node.js, PostgreSQL, Docker,
AWS, Git, REST APIs, MongoDB

Education
B.Tech Computer Science, Delhi University, 2022-2026
12th CBSE, DPS School, 2022

Projects
CloudNote — A cloud-based note-taking app using React and Node.js with MongoDB backend.
PortfoliAI — AI-powered portfolio generator built with Python, Flask, and PostgreSQL.
ChatBot — A simple chatbot using Python and NLTK for natural language processing.

Work Experience
Software Intern at Google India
Open Source Contributor at Mozilla

Achievements
Google Cloud Certified Associate
AWS Solutions Architect Certification
Winner, National Coding Championship 2025
"""


# ============================================================
# TEST 1: Experience storage
# ============================================================

print()
print("=" * 55)
print("TEST 1: Experience extraction and storage")
print("=" * 55)

result, _ = pipeline.parse(full_resume)

check(
    "Experience list is not empty",
    len(result.experience) > 0,
    f"Got: {result.experience}"
)

check(
    "Experience contains intern reference",
    any("intern" in e.lower() or "google" in e.lower()
        for e in result.experience),
    f"Got: {result.experience}"
)

check(
    "experience_text() returns string",
    isinstance(result.experience_text(), str)
)

check(
    "experience_text() is non-empty",
    len(result.experience_text()) > 0,
    f"Got: '{result.experience_text()}'"
)

check(
    "experience_text() uses pipe separator",
    " | " in result.experience_text() or len(result.experience) == 1,
    f"Got: '{result.experience_text()}'"
)


# ============================================================
# TEST 2: Achievements storage
# ============================================================

print()
print("=" * 55)
print("TEST 2: Achievements extraction and storage")
print("=" * 55)

check(
    "Achievements list is not empty",
    len(result.achievements) > 0,
    f"Got: {result.achievements}"
)

check(
    "Achievements contains certification",
    any("certif" in a.lower() or "champion" in a.lower()
        for a in result.achievements),
    f"Got: {result.achievements}"
)

check(
    "achievements_text() returns string",
    isinstance(result.achievements_text(), str)
)

check(
    "achievements_text() is non-empty",
    len(result.achievements_text()) > 0,
    f"Got: '{result.achievements_text()}'"
)


# ============================================================
# TEST 3: Project technologies, github_url, live_url
# ============================================================

print()
print("=" * 55)
print("TEST 3: Project data completeness")
print("=" * 55)

check(
    "Multiple projects parsed",
    len(result.projects) >= 2,
    f"Got {len(result.projects)} projects"
)

# Check project 1 (CloudNote)
if len(result.projects) >= 1:
    p1 = result.projects[0]
    p1_techs = [t.lower() for t in p1.technologies]

    check(
        "Project 1 has title",
        len(p1.title) > 0,
        f"Got: '{p1.title}'"
    )

    check(
        "Project 1 has description",
        len(p1.description) > 0,
        f"Got: '{p1.description}'"
    )

    check(
        "Project 1 has technologies extracted",
        len(p1.technologies) > 0,
        f"Got: {p1.technologies}"
    )

    check(
        "Project 1 detects React",
        "react" in p1_techs,
        f"Technologies: {p1.technologies}"
    )

    check(
        "Project 1 detects Node.js",
        "node.js" in p1_techs,
        f"Technologies: {p1.technologies}"
    )

    check(
        "Project 1 detects MongoDB",
        "mongodb" in p1_techs,
        f"Technologies: {p1.technologies}"
    )

# Check project 2 (PortfoliAI)
if len(result.projects) >= 2:
    p2 = result.projects[1]
    p2_techs = [t.lower() for t in p2.technologies]

    check(
        "Project 2 detects Python",
        "python" in p2_techs,
        f"Technologies: {p2.technologies}"
    )

    check(
        "Project 2 detects Flask",
        "flask" in p2_techs,
        f"Technologies: {p2.technologies}"
    )

    check(
        "Project 2 detects PostgreSQL",
        "postgresql" in p2_techs or "postgres" in p2_techs,
        f"Technologies: {p2.technologies}"
    )


# Test ProjectData model completeness
test_project = ProjectData(
    title="Test",
    description="A test project",
    technologies=["Python", "Flask"],
    github_url="https://github.com/user/repo",
    live_url="https://example.com"
)

check(
    "ProjectData stores github_url",
    test_project.github_url == "https://github.com/user/repo"
)

check(
    "ProjectData stores live_url",
    test_project.live_url == "https://example.com"
)

check(
    "ProjectData technologies is list",
    isinstance(test_project.technologies, list)
    and len(test_project.technologies) == 2
)


# ============================================================
# TEST 4: Parser metadata (parser_used)
# ============================================================

print()
print("=" * 55)
print("TEST 4: Parser metadata")
print("=" * 55)

result2, parser_name = pipeline.parse(full_resume)

check(
    "parser_name is returned",
    parser_name is not None and len(parser_name) > 0,
    f"Got: '{parser_name}'"
)

check(
    "parser_name is 'Enhanced Regex'",
    parser_name == "Enhanced Regex",
    f"Got: '{parser_name}'"
)

check(
    "parser_used stored in ResumeData",
    result2.parser_used == "Enhanced Regex",
    f"Got: '{result2.parser_used}'"
)

check(
    "confidence is computed",
    result2.confidence > 0.0,
    f"Got: {result2.confidence}"
)

check(
    "confidence is between 0 and 1",
    0.0 <= result2.confidence <= 1.0,
    f"Got: {result2.confidence}"
)


# ============================================================
# TEST 5: Data safety (COALESCE protection)
# ============================================================

print()
print("=" * 55)
print("TEST 5: Data safety (empty values)")
print("=" * 55)

# Parse a minimal resume that only has a name
minimal_resume = """
Jane Smith
"""

minimal_result, _ = pipeline.parse(minimal_resume)

check(
    "Minimal parse: name extracted",
    minimal_result.name == "Jane Smith",
    f"Got: '{minimal_result.name}'"
)

check(
    "Minimal parse: email is None (not crash)",
    minimal_result.email is None
)

check(
    "Minimal parse: summary is None (not crash)",
    minimal_result.summary is None
)

check(
    "Minimal parse: skills is empty list",
    minimal_result.skills == []
)

check(
    "Minimal parse: projects is empty list",
    minimal_result.projects == []
)

check(
    "Minimal parse: experience is empty list",
    minimal_result.experience == []
)

check(
    "Minimal parse: achievements is empty list",
    minimal_result.achievements == []
)

# Verify DB helper methods return empty strings (not None/crash)
check(
    "Empty skills_text() returns ''",
    minimal_result.skills_text() == ""
)

check(
    "Empty education_text() returns ''",
    minimal_result.education_text() == ""
)

check(
    "Empty experience_text() returns ''",
    minimal_result.experience_text() == ""
)

check(
    "Empty achievements_text() returns ''",
    minimal_result.achievements_text() == ""
)

# Test 'name or ""' pattern used in main.py
check(
    "'name or empty' for COALESCE: non-None",
    (minimal_result.name or "") == "Jane Smith"
)

check(
    "'email or empty' for COALESCE: None becomes ''",
    (minimal_result.email or "") == ""
)

check(
    "'summary or empty' for COALESCE: None becomes ''",
    (minimal_result.summary or "") == ""
)


# ============================================================
# TEST 6: ResumeData validation edge cases
# ============================================================

print()
print("=" * 55)
print("TEST 6: Pydantic validation edge cases")
print("=" * 55)

# Email validation
check(
    "Invalid email (no @) becomes None",
    ResumeData(email="notanemail").email is None
)

check(
    "Valid email preserved",
    ResumeData(email="user@example.com").email == "user@example.com"
)

check(
    "Email with whitespace stripped",
    ResumeData(email="  user@example.com  ").email == "user@example.com"
)

# Name validation
check(
    "Empty name becomes None",
    ResumeData(name="").name is None
)

check(
    "Whitespace-only name becomes None",
    ResumeData(name="   ").name is None
)

check(
    "Valid name preserved",
    ResumeData(name="  John Doe  ").name == "John Doe"
)

# Skill dedup
check(
    "Skills case-insensitive dedup",
    ResumeData(skills=["Python", "python", "PYTHON"]).skills == ["Python"]
)

check(
    "Skills whitespace stripped",
    ResumeData(skills=["  React  ", "  react  "]).skills == ["React"]
)

check(
    "Empty skills filtered out",
    ResumeData(skills=["Python", "", "  ", "Java"]).skills == ["Python", "Java"]
)

# Non-string skills filtered
check(
    "Non-string skills filtered",
    ResumeData(skills=["Python", 123, None, "Java"]).skills == ["Python", "Java"]
)


# ============================================================
# TEST 7: Full pipeline round-trip
# ============================================================

print()
print("=" * 55)
print("TEST 7: Full pipeline round-trip")
print("=" * 55)

result3, name3 = pipeline.parse(full_resume)

# Simulate what main.py does
name_for_db = result3.name or ""
email_for_db = result3.email or ""
bio_for_db = result3.summary or ""
skills_for_db = result3.skills_text()
education_for_db = result3.education_text()
experience_for_db = result3.experience_text()
achievements_for_db = result3.achievements_text()
parser_for_db = name3

check(
    "name for DB is non-empty string",
    len(name_for_db) > 0,
    f"Got: '{name_for_db}'"
)

check(
    "email for DB is non-empty string",
    len(email_for_db) > 0,
    f"Got: '{email_for_db}'"
)

check(
    "bio for DB is non-empty string",
    len(bio_for_db) > 0,
    f"Got: '{bio_for_db}'"
)

check(
    "skills for DB is comma-separated",
    "," in skills_for_db,
    f"Got: '{skills_for_db}'"
)

check(
    "education for DB is non-empty",
    len(education_for_db) > 0,
    f"Got: '{education_for_db}'"
)

check(
    "experience for DB is non-empty",
    len(experience_for_db) > 0,
    f"Got: '{experience_for_db}'"
)

check(
    "achievements for DB is non-empty",
    len(achievements_for_db) > 0,
    f"Got: '{achievements_for_db}'"
)

check(
    "parser_used for DB is set",
    parser_for_db == "Enhanced Regex",
    f"Got: '{parser_for_db}'"
)

# Simulate project INSERT values
for i, proj in enumerate(result3.projects):
    techs_for_db = ", ".join(proj.technologies)

    check(
        f"Project {i+1} title non-empty",
        len(proj.title) > 0,
        f"Got: '{proj.title}'"
    )

    check(
        f"Project {i+1} technologies string",
        isinstance(techs_for_db, str),
        f"Got: '{techs_for_db}'"
    )

    check(
        f"Project {i+1} github_url is str or None",
        proj.github_url is None or isinstance(proj.github_url, str)
    )

    check(
        f"Project {i+1} live_url is str or None",
        proj.live_url is None or isinstance(proj.live_url, str)
    )


# ============================================================
# TEST 8: Pipeline fallback robustness
# ============================================================

print()
print("=" * 55)
print("TEST 8: Pipeline fallback robustness")
print("=" * 55)

# Empty input
empty_result, empty_parser = pipeline.parse("")
check(
    "Empty string: does not crash",
    empty_result is not None
)
check(
    "Empty string: returns Enhanced Regex",
    empty_parser == "Enhanced Regex"
)
check(
    "Empty string: experience is []",
    empty_result.experience == []
)
check(
    "Empty string: achievements is []",
    empty_result.achievements == []
)

# None-like input
space_result, _ = pipeline.parse("   \n\n   ")
check(
    "Whitespace-only: does not crash",
    space_result is not None
)

# Gibberish
gib_result, _ = pipeline.parse("!@#$%^&*() 12345 ???")
check(
    "Gibberish: does not crash",
    gib_result is not None
)
check(
    "Gibberish: all DB helpers return strings",
    isinstance(gib_result.skills_text(), str)
    and isinstance(gib_result.experience_text(), str)
    and isinstance(gib_result.achievements_text(), str)
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 55)

total = passed + failed

if failed == 0:
    print(f"ALL {total} TESTS PASSED")
else:
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")

print("=" * 55)

if __name__ == "__main__":
    sys.exit(0 if failed == 0 else 1)
