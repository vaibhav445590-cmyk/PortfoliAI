"""
PortfoliAI — Centralized Configuration Management
Provides clean environment-driven settings for Development and Production.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Production and Development Configuration Settings."""

    # Environment
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
    SECRET_KEY = os.getenv("SECRET_KEY", "portfoliai-default-dev-secret-change-in-production")

    # Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "student_portfolio")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DATABASE_URL = os.getenv("DATABASE_URL")

    # JWT Authentication
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

    # Uploads & File Restrictions
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join("uploads", "resumes"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(10 * 1024 * 1024)))  # 10 MB
    ALLOWED_EXTENSIONS = {"pdf"}

    # AI & Service Providers
    AI_PROVIDER = os.getenv("AI_PROVIDER", "local").lower()
    AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "15"))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # Rate Limiting & Abuse Protection
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    @classmethod
    def get_db_params(cls) -> dict:
        """Return a connection dict suitable for psycopg2.connect()."""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "database": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
        }
