"""
Database dependencies module for FastAPI dependency injection.
"""
from app.db.session import get_db, SessionLocal

__all__ = ["get_db", "SessionLocal"]