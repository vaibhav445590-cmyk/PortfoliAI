"""
PortfoliAI — Data Access Repositories Package
Decouples database operations from route handlers and business logic.
"""

from .user_repository import UserRepository
from .student_repository import StudentRepository
from .project_repository import ProjectRepository

__all__ = ["UserRepository", "StudentRepository", "ProjectRepository"]
