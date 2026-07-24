"""
src/api/main.py

Run with:
    uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

(run from the backend/ directory so the src/ imports resolve correctly --
 or set PYTHONPATH=src, see note in README)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db.postgres import init_db
from api.routes import people, detect, logs, dashboard

app = FastAPI(title="SafeGuardAI Face Recognition API", version="0.1.0")

# Wide open for local dev -- tighten this to your actual frontend origin
# before deploying anywhere public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(people.router)
app.include_router(detect.router)
app.include_router(logs.router)
app.include_router(dashboard.router)

# Serve processed images/videos and enrollment photos so the frontend can
# display them directly via URL, e.g. GET /files/uploads/outputs/123_video.mp4
os.makedirs("data", exist_ok=True)
app.mount("/files", StaticFiles(directory="data"), name="files")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
async def root():
    return {"status": "ok", "service": "SafeGuardAI Face Recognition API"}