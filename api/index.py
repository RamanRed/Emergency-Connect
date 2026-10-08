"""Vercel serverless entrypoint. Re-exports the FastAPI app."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.server import app  # noqa: E402,F401
