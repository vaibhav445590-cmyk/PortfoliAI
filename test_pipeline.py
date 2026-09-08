"""
PortfoliAI — Pipeline Integration Test

Tests the new parser pipeline with sample resume text
to verify:
    1. Pipeline creates and registers parsers
    2. Enhanced regex parser produces ResumeData
    3. All fields are correctly extracted
    4. Technologies are extracted from project text
    5. Confidence scoring works
    6. Database helper methods work
    7. Fallback behavior works
"""

import sys
sys.path.insert(0, ".")

from parser_pipeline import create_default_pipeline
from resume_data import ResumeData, ProjectData


# ============================================================
# TEST 1: Pipeline creation
# ============================================================

print("=" * 50)
print("TEST 1: Pipeline creation")
print("=" * 50)

pipeline = create_default_pipeline()

print(f"Registered parsers: {len(pipeline.parsers)}")

for p in pipeline.parsers:
    print(f"  - {p.name()} (available: {p.is_available()})")

assert len(pipeline.parsers) >= 1, "Pipeline must have at least one parser"
assert pipeline.parsers[0].is_available(), "Regex parser must always be available"

print("PASS\n")


# ============================================================
# TEST 2: Parse sample resume
# ============================================================

print("=" * 50)
print("TEST 2: Parse sample resume")
print("=" * 50)

sample_resume = """
Alex Sharma
BCA Student | Aspiring Software Developer
Email: alex.sharma@example.com
Phone: +91 9000000000

Summary
Motivated BCA student interested in backend development, APIs, databases, and software engineering.

Technical Skills
Python, FastAPI, PostgreSQL, Git, REST APIs, HTML, SQL

Education
BCA — Guru Gobind Singh Indraprastha University, 2023-2026

Projects
Student Portfolio — A portfolio website built using Flask and PostgreSQL.
Weather Dashboard — A real-time weather app using Python and OpenWeatherMap API.

Experience
Backend Development Intern at TechStartup Inc.

Achievements
Completed Python certification
"""

result, parser_name = pipeline.parse(sample_resume)

print(f"Parser used: {parser_name}")
print(f"Confidence:  {result.confidence}")
print()
print(f"Name:        {result.name}")
print(f"Email:       {result.email}")
print(f"Phone:       {result.phone}")
print(f"Summary:     {result.summary}")
print(f"Skills:      {result.skills}")
print(f"Education:   {result.education}")
print(f"Projects:    {len(result.projects)}")

for i, p in enumerate(result.projects):
    print(f"  Project {i+1}: {p.title}")
    print(f"    Description:  {p.description}")
    print(f"    Technologies: {p.technologies}")

print(f"Experience:  {result.experience}")
print(f"Achievements: {result.achievements}")

# Assertions
assert result.name == "Alex Sharma", f"Expected 'Alex Sharma', got '{result.name}'"
assert result.email == "alex.sharma@example.com", f"Email mismatch: {result.email}"
assert result.phone is not None, "Phone should be extracted"
assert result.summary is not None, "Summary should be extracted"
assert len(result.skills) > 0, "Skills should be extracted"
assert len(result.education) > 0, "Education should be extracted"
assert len(result.projects) == 2, f"Expected 2 projects, got {len(result.projects)}"
assert result.confidence > 0.5, f"Confidence too low: {result.confidence}"
assert parser_name == "Enhanced Regex", f"Wrong parser: {parser_name}"

print("\nPASS\n")


# ============================================================
# TEST 3: Technologies extraction
# ============================================================

print("=" * 50)
print("TEST 3: Technologies extraction")
print("=" * 50)

# The first project mentions Flask and PostgreSQL
p1_techs = [t.lower() for t in result.projects[0].technologies]
print(f"Project 1 techs: {result.projects[0].technologies}")

assert "flask" in p1_techs, f"Flask should be detected in project 1"
assert "postgresql" in p1_techs or "postgres" in p1_techs, \
    f"PostgreSQL should be detected in project 1"

# The second project mentions Python
p2_techs = [t.lower() for t in result.projects[1].technologies]
print(f"Project 2 techs: {result.projects[1].technologies}")

assert "python" in p2_techs, f"Python should be detected in project 2"

print("PASS\n")


# ============================================================
# TEST 4: Database helper methods
# ============================================================

print("=" * 50)
print("TEST 4: Database helper methods")
print("=" * 50)

skills_text = result.skills_text()
education_text = result.education_text()

print(f"skills_text():    {skills_text}")
print(f"education_text(): {education_text}")

assert isinstance(skills_text, str), "skills_text() should return string"
assert isinstance(education_text, str), "education_text() should return string"
assert len(skills_text) > 0, "skills_text() should not be empty"

print("PASS\n")


# ============================================================
# TEST 5: Skill deduplication
# ============================================================

print("=" * 50)
print("TEST 5: Skill deduplication (case-insensitive)")
print("=" * 50)

dedup_data = ResumeData(
    skills=["Python", "python", "PYTHON", "Java", "java"]
)

print(f"Input:  ['Python', 'python', 'PYTHON', 'Java', 'java']")
print(f"Output: {dedup_data.skills}")

assert len(dedup_data.skills) == 2, f"Expected 2 unique skills, got {len(dedup_data.skills)}"

print("PASS\n")


# ============================================================
# TEST 6: Empty/malformed input handling
# ============================================================

print("=" * 50)
print("TEST 6: Empty/malformed input handling")
print("=" * 50)

empty_result, _ = pipeline.parse("")
print(f"Empty string: name={empty_result.name}, confidence={empty_result.confidence}")
assert empty_result is not None, "Empty input should not crash"

none_result, _ = pipeline.parse("   ")
print(f"Whitespace:   name={none_result.name}, confidence={none_result.confidence}")
assert none_result is not None, "Whitespace input should not crash"

gibberish_result, _ = pipeline.parse("asdlkfjasl;dkfj 12345 @@@ !!!")
print(f"Gibberish:    name={gibberish_result.name}, confidence={gibberish_result.confidence}")
assert gibberish_result is not None, "Gibberish should not crash"

print("PASS\n")


# ============================================================
# TEST 7: Fuzzy section header matching
# ============================================================

print("=" * 50)
print("TEST 7: Fuzzy section header matching")
print("=" * 50)

fuzzy_resume = """
John Doe

PROFESSIONAL SUMMARY
Experienced software developer with 5 years of experience.

TECHNICAL SKILLS & TOOLS
JavaScript, React, Node.js, Docker, AWS

KEY PROJECTS
E-commerce Platform — Built a full-stack web application using React and Node.js
"""

fuzzy_result, _ = pipeline.parse(fuzzy_resume)

print(f"Name:     {fuzzy_result.name}")
print(f"Summary:  {fuzzy_result.summary}")
print(f"Skills:   {fuzzy_result.skills}")
print(f"Projects: {len(fuzzy_result.projects)}")

assert fuzzy_result.name == "John Doe", f"Name mismatch: {fuzzy_result.name}"
assert fuzzy_result.summary is not None, "Summary should be found via fuzzy match"
assert len(fuzzy_result.skills) > 0, "Skills should be found via fuzzy match"
assert len(fuzzy_result.projects) > 0, "Projects should be found via fuzzy match"

print("PASS\n")


# ============================================================
# SUMMARY
# ============================================================

print("=" * 50)
print("ALL TESTS PASSED")
print("=" * 50)
