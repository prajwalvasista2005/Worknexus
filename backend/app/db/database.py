"""
Database engine and session factory module.
Re-exports canonical engine, SessionLocal, and get_db from session.py to eliminate dual-engine duplication.
"""
from app.db.session import engine, SessionLocal, get_db

__all__ = ["engine", "SessionLocal", "get_db"]