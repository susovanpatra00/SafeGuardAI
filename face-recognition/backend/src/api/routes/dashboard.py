"""
src/api/routes/dashboard.py
"""

from fastapi import APIRouter
from sqlalchemy import func, cast, Date
from datetime import datetime, timezone

from db.postgres import get_session, Person, RecognitionLog
from api.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    session = get_session()
    try:
        today = datetime.now(timezone.utc).date()

        total_enrolled = session.query(func.count(Person.id)).scalar()

        recognitions_today = (
            session.query(func.count(RecognitionLog.id))
            .filter(cast(RecognitionLog.created_at, Date) == today)
            .scalar()
        )

        unknown_today = (
            session.query(func.count(RecognitionLog.id))
            .filter(cast(RecognitionLog.created_at, Date) == today)
            .filter(RecognitionLog.status == "unknown")
            .scalar()
        )

        active_sources_today = (
            session.query(func.count(func.distinct(RecognitionLog.source)))
            .filter(cast(RecognitionLog.created_at, Date) == today)
            .scalar()
        )

        return DashboardStats(
            total_enrolled_faces=total_enrolled or 0,
            recognitions_today=recognitions_today or 0,
            unknown_faces_flagged_today=unknown_today or 0,
            active_sources_today=active_sources_today or 0,
        )
    finally:
        session.close()