"""
WorkNexus Core Configuration Module Alias
Re-exports settings and Settings from app.config.
"""
from app.config import settings, Settings

__all__ = ["settings", "Settings"]
