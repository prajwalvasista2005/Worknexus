import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo_dir = os.path.dirname(backend_dir)
for p in (backend_dir, repo_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from .main import app, create_app

__all__ = ["app", "create_app"]
