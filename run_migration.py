"""
PortfoliAI — Database Migration Runner

Safely applies schema migrations to the existing
student_portfolio database.

Features:
    - Idempotent (safe to run multiple times)
    - Preserves all existing data
    - Reports what was added vs already existed

Usage:
    python run_migration.py
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

import psycopg2
from config import Config


def get_db_connection():
    return psycopg2.connect(**Config.get_db_params())


def check_column_exists(cursor, table, column):
    """Check if a column exists in a table."""

    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s
            AND column_name = %s
        )
        """,
        (table, column)
    )

    return cursor.fetchone()[0]


def run_migration():

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        print("=" * 55)
        print("PortfoliAI — Database Migration")
        print("=" * 55)
        print()


        # ======================================================
        # CHECK CONNECTION
        # ======================================================

        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"Connected: {version[:40]}...")
        print()


        # ======================================================
        # VERIFY TABLES EXIST
        # ======================================================

        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'students'
            )
            """
        )

        if not cursor.fetchone()[0]:
            print("ERROR: 'students' table does not exist.")
            print("Create it first using schema.sql.")
            return False

        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = 'projects'
            )
            """
        )

        if not cursor.fetchone()[0]:
            print("ERROR: 'projects' table does not exist.")
            print("Create it first using schema.sql.")
            return False

        print("Tables verified: students, projects")
        print()


        # ======================================================
        # MIGRATE STUDENTS TABLE
        # ======================================================

        print("--- Students table ---")

        new_columns = {
            "experience":         "TEXT",
            "achievements":       "TEXT",
            "parser_used":        "TEXT",
            "headline":           "TEXT",
            "categorized_skills": "TEXT",
            "ai_provider":        "TEXT",
            "resume_hash":        "TEXT",
            "processing_status":  "TEXT",
            "last_processed_at":  "TIMESTAMP WITH TIME ZONE",
        }

        for column, col_type in new_columns.items():

            exists = check_column_exists(
                cursor, "students", column
            )

            if exists:
                print(f"  {column}: already exists (skipped)")

            else:
                cursor.execute(
                    f"ALTER TABLE students ADD COLUMN {column} {col_type}"
                )
                print(f"  {column}: ADDED ({col_type})")

        print()


        # ======================================================
        # VERIFY PROJECTS TABLE COLUMNS
        # ======================================================

        print("--- Projects table ---")

        project_columns = {
            "technologies": "TEXT",
            "github_url":   "TEXT",
            "live_url":     "TEXT",
            "category":     "TEXT",
        }

        for column, col_type in project_columns.items():

            exists = check_column_exists(
                cursor, "projects", column
            )

            if exists:
                print(f"  {column}: exists (OK)")
            else:
                cursor.execute(
                    f"ALTER TABLE projects ADD COLUMN {column} {col_type}"
                )
                print(f"  {column}: ADDED ({col_type})")

        print()

        # ======================================================
        # PHASE 4 MIGRATIONS: USERS TABLE & INDEXES
        # ======================================================

        print("--- Phase 4: Users & Ownership ---")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            SERIAL PRIMARY KEY,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        print("  users table: verified / created (OK)")

        # Check user_id in students
        if check_column_exists(cursor, "students", "user_id"):
            print("  students.user_id: exists (OK)")
        else:
            cursor.execute("ALTER TABLE students ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
            print("  students.user_id: ADDED (INTEGER REFERENCES users)")

        print()
        print("--- Phase 4: Production Indexes ---")
        indexes = [
            ("idx_projects_student_id", "CREATE INDEX IF NOT EXISTS idx_projects_student_id ON projects(student_id)"),
            ("idx_students_email", "CREATE INDEX IF NOT EXISTS idx_students_email ON students(email)"),
            ("idx_students_resume_hash", "CREATE INDEX IF NOT EXISTS idx_students_resume_hash ON students(resume_hash)"),
            ("idx_students_user_id", "CREATE INDEX IF NOT EXISTS idx_students_user_id ON students(user_id)"),
            ("idx_users_email", "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"),
        ]

        for idx_name, idx_sql in indexes:
            cursor.execute(idx_sql)
            print(f"  {idx_name}: verified / created (OK)")

        print()

        # ======================================================
        # PHASE 5 MIGRATIONS: PORTFOLIO SETTINGS & CUSTOMIZATION
        # ======================================================

        print("--- Phase 5: Portfolio Settings & Customization ---")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_settings (
                id                  SERIAL PRIMARY KEY,
                student_id          INTEGER UNIQUE NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                template            TEXT NOT NULL DEFAULT 'default',
                theme               TEXT NOT NULL DEFAULT 'glass',
                accent              TEXT NOT NULL DEFAULT 'emerald',
                status              TEXT NOT NULL DEFAULT 'published',
                section_visibility  JSONB NOT NULL DEFAULT '{"about": true, "skills": true, "education": true, "experience": true, "projects": true, "achievements": true}'::jsonb,
                project_order       JSONB NOT NULL DEFAULT '[]'::jsonb,
                social_links        JSONB NOT NULL DEFAULT '{}'::jsonb,
                custom_headline     TEXT,
                custom_bio          TEXT,
                custom_name         TEXT,
                created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        print("  portfolio_settings table: verified / created (OK)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_settings_student_id ON portfolio_settings(student_id);")
        print("  idx_portfolio_settings_student_id: verified / created (OK)")
        print()

        # ======================================================
        # VERIFY EXISTING DATA IS INTACT
        # ======================================================

        print("--- Data check ---")

        cursor.execute("SELECT COUNT(*) FROM students")
        student_count = cursor.fetchone()[0]
        print(f"  Students: {student_count} record(s)")

        cursor.execute("SELECT COUNT(*) FROM projects")
        project_count = cursor.fetchone()[0]
        print(f"  Projects: {project_count} record(s)")

        cursor.execute("SELECT COUNT(*) FROM portfolio_settings")
        settings_count = cursor.fetchone()[0]
        print(f"  Portfolio Settings: {settings_count} record(s)")

        print()


        # ======================================================
        # COMMIT
        # ======================================================

        conn.commit()

        print("=" * 55)
        print("Migration completed successfully.")
        print("All existing data preserved.")
        print("=" * 55)

        return True


    except Exception as e:

        if conn:
            conn.rollback()

        print(f"\nMigration failed: {e}")
        return False


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


if __name__ == "__main__":

    success = run_migration()

    sys.exit(0 if success else 1)
