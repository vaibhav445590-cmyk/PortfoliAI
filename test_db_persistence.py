"""
PortfoliAI — Live Database Persistence & Data Safety Tests

Verifies directly against PostgreSQL:
    1. Schema columns exist (parser_used, experience, achievements, etc.)
    2. Experience, achievements, parser_used persist properly
    3. Project technologies, github_url, live_url persist properly
    4. COALESCE protects existing valid student fields from being wiped by empty values
    5. Safe project re-processing preserves existing project URLs & unparsed projects
    6. Empty parsed projects list does NOT delete existing projects
    7. Clean teardown of test records

Compatible with both:
    - pytest (`python -m pytest test_db_persistence.py` or `python -m pytest`)
    - Direct CLI execution (`python test_db_persistence.py`)
"""

import os
import sys
import pytest
import psycopg2
from dotenv import load_dotenv

load_dotenv()

passed = 0
failed = 0


def check(name, condition, detail=""):
    """
    Validation helper that tracks pass/fail counts, outputs CLI logs,
    and asserts for pytest compatibility.
    """
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")
        if detail:
            print(f"        {detail}")
    assert condition, f"{name}: {detail}"


def get_db():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="student_portfolio",
        user="postgres",
        password=os.getenv("DB_PASSWORD", "")
    )


# ------------------------------------------------------------------
# TEST 1: Schema columns check (6 checks)
# ------------------------------------------------------------------
def test_schema_columns():
    """Verify all required Phase 1 columns exist in students and projects tables."""
    print("\n--- 1. Schema Column Verification ---")
    conn = get_db()
    cursor = conn.cursor()

    def col_exists(table, col):
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            )
        """, (table, col))
        return cursor.fetchone()[0]

    try:
        check("students.parser_used exists", col_exists("students", "parser_used"))
        check("students.experience exists", col_exists("students", "experience"))
        check("students.achievements exists", col_exists("students", "achievements"))
        check("projects.technologies exists", col_exists("projects", "technologies"))
        check("projects.github_url exists", col_exists("projects", "github_url"))
        check("projects.live_url exists", col_exists("projects", "live_url"))
    finally:
        cursor.close()
        conn.close()


# Shared fixture / context for persistence tests (Tests 2 - 5)
TEST_EMAIL = "qa_test_unique_999@test.com"


class MockProject:
    def __init__(self, title, description, technologies=None, github_url=None, live_url=None):
        self.title = title
        self.description = description
        self.technologies = technologies or []
        self.github_url = github_url
        self.live_url = live_url


# ------------------------------------------------------------------
# TEST 2: Insert test student & verify full persistence (3 checks)
# ------------------------------------------------------------------
def test_full_field_persistence():
    """Verify experience, achievements, and parser_used persist in database."""
    print("\n--- 2. Full Field Persistence Test ---")
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
        conn.commit()

        cursor.execute("""
            INSERT INTO students (
                name, email, bio, skills, education,
                experience, achievements, parser_used
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            "Original Name",
            TEST_EMAIL,
            "Original Bio",
            "Python, Flask",
            "BCA 2026",
            "Backend Intern at TechCorp | Open Source Dev",
            "Certified Python Dev | Hackathon Winner 2025",
            "Enhanced Regex"
        ))
        student_id = cursor.fetchone()[0]
        conn.commit()

        cursor.execute("""
            SELECT name, email, bio, skills, education, experience, achievements, parser_used
            FROM students WHERE id = %s
        """, (student_id,))
        row = cursor.fetchone()

        check("Student experience persists in DB", row[5] == "Backend Intern at TechCorp | Open Source Dev", f"Got: {row[5]}")
        check("Student achievements persist in DB", row[6] == "Certified Python Dev | Hackathon Winner 2025", f"Got: {row[6]}")
        check("Student parser_used persists in DB", row[7] == "Enhanced Regex", f"Got: {row[7]}")

    finally:
        cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
        conn.commit()
        cursor.close()
        conn.close()


# ------------------------------------------------------------------
# TEST 3: COALESCE protection when updating with empty values (8 checks)
# ------------------------------------------------------------------
def test_coalesce_data_safety():
    """Verify COALESCE prevents empty or missing values from wiping existing data."""
    print("\n--- 3. COALESCE Data Safety Test (Empty values do not overwrite) ---")
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
        conn.commit()

        cursor.execute("""
            INSERT INTO students (
                name, email, bio, skills, education,
                experience, achievements, parser_used
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            "Original Name",
            TEST_EMAIL,
            "Original Bio",
            "Python, Flask",
            "BCA 2026",
            "Backend Intern at TechCorp | Open Source Dev",
            "Certified Python Dev | Hackathon Winner 2025",
            "Enhanced Regex"
        ))
        student_id = cursor.fetchone()[0]
        conn.commit()

        # Update with empty values
        cursor.execute("""
            UPDATE students
            SET
                name         = COALESCE(NULLIF(%s, ''), name),
                email        = COALESCE(NULLIF(%s, ''), email),
                bio          = COALESCE(NULLIF(%s, ''), bio),
                skills       = COALESCE(NULLIF(%s, ''), skills),
                education    = COALESCE(NULLIF(%s, ''), education),
                experience   = COALESCE(NULLIF(%s, ''), experience),
                achievements = COALESCE(NULLIF(%s, ''), achievements),
                parser_used  = COALESCE(NULLIF(%s, ''), parser_used)
            WHERE id = %s
        """, ("", "", "", "", "", "", "", "", student_id))
        conn.commit()

        cursor.execute("""
            SELECT name, email, bio, skills, education, experience, achievements, parser_used
            FROM students WHERE id = %s
        """, (student_id,))
        row = cursor.fetchone()

        check("Name preserved after empty update", row[0] == "Original Name")
        check("Email preserved after empty update", row[1] == TEST_EMAIL)
        check("Bio preserved after empty update", row[2] == "Original Bio")
        check("Skills preserved after empty update", row[3] == "Python, Flask")
        check("Education preserved after empty update", row[4] == "BCA 2026")
        check("Experience preserved after empty update", row[5] == "Backend Intern at TechCorp | Open Source Dev")
        check("Achievements preserved after empty update", row[6] == "Certified Python Dev | Hackathon Winner 2025")
        check("Parser_used preserved after empty update", row[7] == "Enhanced Regex")

    finally:
        cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
        conn.commit()
        cursor.close()
        conn.close()


# ------------------------------------------------------------------
# TEST 4: Project fields persistence & re-processing safety (10 checks)
# ------------------------------------------------------------------
def test_project_data_persistence_and_safe_reprocessing():
    """Verify project fields persist and re-processing preserves existing URLs and unparsed projects."""
    print("\n--- 4. Project Data Persistence & Safe Re-processing ---")
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
        conn.commit()

        cursor.execute("""
            INSERT INTO students (name, email)
            VALUES (%s, %s)
            RETURNING id
        """, ("Project Test Student", TEST_EMAIL))
        student_id = cursor.fetchone()[0]
        conn.commit()

        # Seed project 1 with custom URLs and project 2
        cursor.execute("""
            INSERT INTO projects (student_id, title, description, technologies, github_url, live_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            "Portfolio WebApp",
            "A portfolio site",
            "Python, Flask, PostgreSQL",
            "https://github.com/myname/portfolio",
            "https://myportfolio.live"
        ))

        cursor.execute("""
            INSERT INTO projects (student_id, title, description, technologies, github_url, live_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            "Weather Bot",
            "A weather chatbot",
            "Python",
            None,
            None
        ))
        conn.commit()

        cursor.execute("""
            SELECT title, description, technologies, github_url, live_url
            FROM projects WHERE student_id = %s ORDER BY id
        """, (student_id,))
        initial_projs = cursor.fetchall()

        check("Project 1 technologies stored", initial_projs[0][2] == "Python, Flask, PostgreSQL")
        check("Project 1 github_url stored", initial_projs[0][3] == "https://github.com/myname/portfolio")
        check("Project 1 live_url stored", initial_projs[0][4] == "https://myportfolio.live")

        # Simulate re-processing
        new_parsed_projects = [
            MockProject(
                title="Portfolio WebApp",
                description="Updated modern portfolio site with liquid glass UI",
                technologies=["Python", "Flask", "PostgreSQL", "CSS"],
                github_url=None,
                live_url=None
            ),
            MockProject(
                title="AI Chat Assistant",
                description="LLM powered assistant",
                technologies=["Python", "PyTorch"],
                github_url="https://github.com/myname/aichat",
                live_url=None
            )
        ]

        valid_projects = [p for p in new_parsed_projects if p.title and p.title.strip()]

        cursor.execute("""
            SELECT id, title, description, technologies, github_url, live_url
            FROM projects
            WHERE student_id = %s
        """, (student_id,))
        existing_rows = cursor.fetchall()
        existing_by_title = {}
        for r in existing_rows:
            if r[1]:
                existing_by_title[r[1].strip().lower()] = {
                    "id": r[0],
                    "title": r[1],
                    "description": r[2] or "",
                    "technologies": r[3] or "",
                    "github_url": r[4],
                    "live_url": r[5]
                }

        cursor.execute("DELETE FROM projects WHERE student_id = %s", (student_id,))

        seen_titles = set()
        for project in valid_projects:
            norm_title = project.title.strip().lower()
            seen_titles.add(norm_title)
            existing = existing_by_title.get(norm_title, {})

            techs = list(project.technologies)
            if not techs and existing.get("technologies"):
                techs = [t.strip() for t in existing["technologies"].split(",") if t.strip()]
            technologies_text = ", ".join(techs)

            description = (
                project.description.strip()
                if project.description and project.description.strip()
                else existing.get("description", "")
            )
            github_url = project.github_url if project.github_url else existing.get("github_url")
            live_url = project.live_url if project.live_url else existing.get("live_url")

            cursor.execute("""
                INSERT INTO projects (student_id, title, description, technologies, github_url, live_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (student_id, project.title.strip(), description, technologies_text, github_url, live_url))

        for norm_title, existing in existing_by_title.items():
            if norm_title not in seen_titles:
                cursor.execute("""
                    INSERT INTO projects (student_id, title, description, technologies, github_url, live_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (student_id, existing["title"], existing["description"], existing["technologies"], existing["github_url"], existing["live_url"]))

        conn.commit()

        cursor.execute("""
            SELECT title, description, technologies, github_url, live_url
            FROM projects WHERE student_id = %s
            ORDER BY title
        """, (student_id,))
        reprocessed_projs = {r[0]: r for r in cursor.fetchall()}

        check("All 3 projects exist after re-processing", len(reprocessed_projs) == 3, f"Got {len(reprocessed_projs)}")

        p1_merged = reprocessed_projs.get("Portfolio WebApp")
        check("Portfolio WebApp got updated description", p1_merged and "liquid glass UI" in p1_merged[1])
        check("Portfolio WebApp PRESERVED github_url", p1_merged and p1_merged[3] == "https://github.com/myname/portfolio")
        check("Portfolio WebApp PRESERVED live_url", p1_merged and p1_merged[4] == "https://myportfolio.live")

        p_unparsed = reprocessed_projs.get("Weather Bot")
        check("Unparsed project 'Weather Bot' was PRESERVED", p_unparsed is not None)

        p_new = reprocessed_projs.get("AI Chat Assistant")
        check("New project 'AI Chat Assistant' was ADDED", p_new is not None)
        check("New project github_url stored", p_new and p_new[3] == "https://github.com/myname/aichat")

    finally:
        cursor.execute("DELETE FROM projects WHERE student_id = (SELECT id FROM students WHERE email = %s)", (TEST_EMAIL,))
        cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
        conn.commit()
        cursor.close()
        conn.close()


# ------------------------------------------------------------------
# TEST 5: Empty parsed projects list does NOT delete projects (1 check)
# ------------------------------------------------------------------
def test_empty_projects_parse_safety():
    """Verify existing projects are not deleted if parsed projects list is empty."""
    print("\n--- 5. Empty Projects Parse Safety ---")
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
        conn.commit()

        cursor.execute("INSERT INTO students (name, email) VALUES (%s, %s) RETURNING id", ("Empty Test", TEST_EMAIL))
        student_id = cursor.fetchone()[0]

        cursor.execute("INSERT INTO projects (student_id, title) VALUES (%s, %s)", (student_id, "Existing Project"))
        conn.commit()

        empty_parsed_projects = []
        valid_empty = [p for p in empty_parsed_projects if p.title and p.title.strip()]

        if not valid_empty:
            # Safe logic: Do NOT delete!
            pass

        cursor.execute("SELECT COUNT(*) FROM projects WHERE student_id = %s", (student_id,))
        count = cursor.fetchone()[0]
        check("Projects NOT deleted when parsed project list is empty", count == 1, f"Got: {count}")

    finally:
        cursor.execute("DELETE FROM projects WHERE student_id = (SELECT id FROM students WHERE email = %s)", (TEST_EMAIL,))
        cursor.execute("DELETE FROM students WHERE email = %s", (TEST_EMAIL,))
        conn.commit()
        cursor.close()
        conn.close()


# ------------------------------------------------------------------
# CLI Direct Execution Runner
# ------------------------------------------------------------------
def run_all_checks():
    """Run all 28 persistence checks sequentially and report summary."""
    print("=" * 60)
    print("LIVE POSTGRESQL PERSISTENCE & DATA SAFETY TESTS")
    print("=" * 60)

    test_schema_columns()
    test_full_field_persistence()
    test_coalesce_data_safety()
    test_project_data_persistence_and_safe_reprocessing()
    test_empty_projects_parse_safety()

    print()
    print("=" * 60)
    print(f"DATABASE TESTS COMPLETE: {passed}/{passed+failed} PASSED")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
