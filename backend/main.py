"""Compatibility entrypoint for local development.

Run from the backend folder with:
    uvicorn main:app --reload
"""

from app.main import app

