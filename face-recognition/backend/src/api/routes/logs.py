"""
src/api/routes/logs.py
"""

from fastapi import APIRouter
from typing import Optional
from sqlalchemy import desc

from db.postgres import get_session, RecognitionLog, Person
from api.schemas import LogsResponse, LogEntry

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=LogsResponse)
async def get_logs(
    status: Optional[str] = None,      # 'known' | 'unknown' | 'spoof'
    source: Optional[str] = None,
    person_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
):
    session = get_session()
    try:
        query = session.query(RecognitionLog, Person.name).outerjoin(
            Person, RecognitionLog.person_id == Person.id
        )

        if status:
            query = query.filter(RecognitionLog.status == status)
        if source:
            query = query.filter(RecognitionLog.source.ilike(f"%{source}%"))
        if person_id:
            query = query.filter(RecognitionLog.person_id == person_id)

        total = query.count()
        rows = query.order_by(desc(RecognitionLog.created_at)).offset(offset).limit(limit).all()

        events = [
            LogEntry(
                id=log.id,
                person_id=log.person_id,
                person_name=name,
                source=log.source,
                timestamp_in_video=log.timestamp_in_video,
                confidence=log.confidence,
                status=log.status,
                created_at=log.created_at,
            )
            for log, name in rows
        ]

        return LogsResponse(total=total, events=events)
    finally:
        session.close()