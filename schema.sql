-- ============================================================
-- PortfoliAI — Database Schema
-- ============================================================
--
-- Database: student_portfolio
-- User:     postgres
--
-- This file documents the complete target schema across Phase 1 and Phase 2.
--
-- For new installations:
--     Run the CREATE TABLE statements.
--
-- For existing installations:
--     Run the MIGRATION sections at the bottom.
--     Or use: python run_migration.py
--
-- All migrations are idempotent (safe to run repeatedly).
-- No existing data is deleted or overwritten.
-- ============================================================


-- ============================================================
-- STUDENTS TABLE (complete target schema)
-- ============================================================

CREATE TABLE IF NOT EXISTS students (
    id                  SERIAL PRIMARY KEY,

    -- Core profile (populated by resume parser)
    name                TEXT,
    email               TEXT,
    bio                 TEXT,          -- parsed summary/objective
    skills              TEXT,          -- comma-separated
    education           TEXT,          -- pipe-separated

    -- Resume storage
    resume_filename     TEXT,          -- original upload filename
    resume_text         TEXT,          -- extracted PDF text

    -- Extended fields (Phase 1)
    experience          TEXT,          -- pipe-separated
    achievements        TEXT,          -- pipe-separated

    -- Parser metadata (Phase 1)
    parser_used         TEXT,          -- parser that extracted the data

    -- AI Intelligence & Enrichment (Phase 2)
    headline            TEXT,          -- professional derived headline
    categorized_skills  TEXT,          -- JSON string of categorized skills
    ai_provider         TEXT,          -- AI provider used (e.g. Local Intelligence, Ollama, OpenAI)
    resume_hash         TEXT,          -- SHA-256 hash of resume_text for caching/re-processing
    processing_status   TEXT,          -- 'pending', 'completed', 'failed'
    last_processed_at   TIMESTAMP WITH TIME ZONE
);


-- ============================================================
-- PROJECTS TABLE (complete target schema)
-- ============================================================

CREATE TABLE IF NOT EXISTS projects (
    id            SERIAL PRIMARY KEY,
    student_id    INTEGER REFERENCES students(id),

    -- Core project data
    title         TEXT,
    description   TEXT,

    -- Extended project data (Phase 1)
    technologies  TEXT,            -- comma-separated
    github_url    TEXT,
    live_url      TEXT,

    -- AI Intelligence & Categorization (Phase 2)
    category      TEXT             -- e.g. "Backend & API Service", "Web Application"
);


-- ============================================================
-- MIGRATIONS (Idempotent)
-- ============================================================

-- Phase 1 additions
ALTER TABLE students ADD COLUMN IF NOT EXISTS experience   TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS achievements TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS parser_used  TEXT;

ALTER TABLE projects ADD COLUMN IF NOT EXISTS technologies TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS github_url   TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS live_url     TEXT;

-- Phase 2 additions
ALTER TABLE students ADD COLUMN IF NOT EXISTS headline            TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS categorized_skills  TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS ai_provider         TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS resume_hash         TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS processing_status   TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS last_processed_at   TIMESTAMP WITH TIME ZONE;

ALTER TABLE projects ADD COLUMN IF NOT EXISTS category            TEXT;

-- Phase 4 additions (Users & Production Indexes)
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE students ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_projects_student_id ON projects(student_id);
CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);
CREATE INDEX IF NOT EXISTS idx_students_resume_hash ON students(resume_hash);
CREATE INDEX IF NOT EXISTS idx_students_user_id ON students(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Phase 5 additions (Portfolio Customization & Settings)
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

CREATE INDEX IF NOT EXISTS idx_portfolio_settings_student_id ON portfolio_settings(student_id);

