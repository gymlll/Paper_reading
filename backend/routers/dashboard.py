"""Dashboard stats router."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Paper, Note
from backend.schemas import DashboardData, DashboardStats, RecentPaper

router = APIRouter()


@router.get("/stats", response_model=DashboardData)
def get_dashboard(db: Session = Depends(get_db)):
    total_papers = db.query(func.count(Paper.id)).scalar()

    month_ago = datetime.utcnow() - timedelta(days=30)
    papers_this_month = (
        db.query(func.count(Paper.id))
        .filter(Paper.created_at >= month_ago)
        .scalar()
    )

    ai_notes_count = (
        db.query(func.count(Note.id))
        .filter(Note.is_ai_generated.in_([1, 2]))
        .scalar()
    )

    pending_papers = (
        db.query(func.count(Paper.id))
        .filter(Paper.status.in_(["uploaded", "parsing"]))
        .scalar()
    )

    recent = (
        db.query(Paper)
        .order_by(Paper.created_at.desc())
        .limit(5)
        .all()
    )

    return DashboardData(
        stats=DashboardStats(
            total_papers=total_papers,
            papers_this_month=papers_this_month,
            ai_notes_count=ai_notes_count,
            pending_papers=pending_papers,
        ),
        recent_papers=[
            RecentPaper(
                id=p.id,
                title=p.title or p.filename,
                status=p.status,
                has_note=p.note is not None,
                created_at=p.created_at,
            )
            for p in recent
        ],
    )
