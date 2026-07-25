"""
Simple shared-secret API key auth.

Every REST and WebSocket endpoint requires ?key=<API_KEY> in the URL.
This is intentionally simple (single shared key, not per-user accounts) --
appropriate for "this server talks to my own cameras and my client's
browser", not for a multi-tenant product. If this grows into something
with multiple customers, swap this for per-camera tokens or real auth.

Set the key via environment variable before starting the server:
    export PERIMETER_API_KEY="some-long-random-string"
    uvicorn main:app --host 0.0.0.0 --port 8000

If you don't set it, a random key is generated each time the server starts
and printed to the log -- fine for local testing, but it means every
client/browser needs the NEW key after every restart. Set a fixed one
before deploying for real.
"""

import os
import secrets
import logging

from fastapi import HTTPException, Query, WebSocket

log = logging.getLogger("auth")

API_KEY = os.environ.get("PERIMETER_API_KEY")

if not API_KEY:
    API_KEY = secrets.token_urlsafe(24)
    log.warning("=" * 70)
    log.warning("PERIMETER_API_KEY environment variable not set!")
    log.warning(f"Generated a TEMPORARY key for this session only: {API_KEY}")
    log.warning("This key will change every restart. For real deployment, set:")
    log.warning('    export PERIMETER_API_KEY="your-own-long-random-string"')
    log.warning("=" * 70)


def verify_key(key: str = Query(..., description="API key (see server startup log / env var)")):
    """Dependency for REST endpoints: adds a required ?key=... query param."""
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def verify_websocket_key(websocket: WebSocket) -> bool:
    """
    Manual check for the websocket endpoint (can't use FastAPI Depends()
    the same way pre-accept). Returns True if the key in the connection's
    query params is valid.
    """
    key = websocket.query_params.get("key")
    return key == API_KEY