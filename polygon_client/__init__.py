"""Polygon API tool layer.

Hand-rolled Python client for the Codeforces Polygon API v1.

Credentials never enter agent/LLM context: `PolygonSession.from_env()` reads
POLYGON_API_KEY / POLYGON_API_SECRET directly from the process environment
(populated from a gitignored `.env`). Agents call the `methods.py` wrappers by
name; they never see the raw key or the signing internals.
"""

from .auth import PolygonSession, PolygonAPIError

__all__ = ["PolygonSession", "PolygonAPIError"]
