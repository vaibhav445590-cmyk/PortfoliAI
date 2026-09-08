"""
PortfoliAI — User Repository
Handles persistence, retrieval, and secure authentication for PortfoliAI users.
"""

from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash


class UserRepository:
    """Repository managing user records and password hashing in PostgreSQL."""

    def __init__(self, db_connection_factory):
        self.get_db_connection = db_connection_factory

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using Werkzeug's secure key derivation."""
        return generate_password_hash(password)

    @staticmethod
    def verify_password(stored_hash: str, password: str) -> bool:
        """Verify a plaintext password against a stored secure hash."""
        if not stored_hash or not password:
            return False
        return check_password_hash(stored_hash, password)

    def create_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Create a new user record with securely hashed password.
        Raises ValueError if email or password are invalid.
        """
        clean_email = (email or "").strip().lower()
        if not clean_email or "@" not in clean_email:
            raise ValueError("Valid email address is required.")
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        pwd_hash = self.hash_password(password)

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s)
                RETURNING id, email, created_at
                """,
                (clean_email, pwd_hash)
            )
            row = cursor.fetchone()
            conn.commit()
            return {
                "id": row[0],
                "email": row[1],
                "created_at": str(row[2]) if row[2] else None
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieve user record by email (including password_hash for auth check)."""
        clean_email = (email or "").strip().lower()
        if not clean_email:
            return None

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, email, password_hash, created_at
                FROM users
                WHERE email = %s
                """,
                (clean_email,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "email": row[1],
                "password_hash": row[2],
                "created_at": str(row[3]) if row[3] else None
            }
        finally:
            cursor.close()
            conn.close()

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve user record by user ID."""
        if not user_id:
            return None

        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, email, password_hash, created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "email": row[1],
                "password_hash": row[2],
                "created_at": str(row[3]) if row[3] else None
            }
        finally:
            cursor.close()
            conn.close()
