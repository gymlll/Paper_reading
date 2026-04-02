"""Paper CRUD router."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Paper, Note
from backend.schemas import PaperCreate, PaperUpdate, PaperOut, PaperDetail, PaperListOut

router = APIRouter()


def _parse_tags(tags_str: Optional[str]) -> Optional[list[str]]:
    if not tags_str:
        return None
    try:
        return json.loads(tags_str)
    except (json.JSONDecodeError, TypeError):
        return [t.strip() for t in tags_str.split(",") if t.strip()]


def _paper_to_out(paper: Paper) -> PaperOut:
    return PaperOut(
        id=paper.id,
        title=paper.title,
        filename=paper.filename,
        authors=paper.authors,
        venue=paper.venue,
        year=paper.year,
        tags=_parse_tags(paper.tags),
        status=paper.status,
        word_count=paper.word_count,
        page_count=paper.page_count,
        has_note=paper.note is not None,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
    )


@router.get("", response_model=PaperListOut)
def list_papers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    year: Optional[int] = None,
    tag: Optional[str] = None,
    sort: str = Query("created_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    # Normalize sort: accept "created_at_desc" style
    if "_" in sort and sort not in ("created_at", "title", "year", "updated_at"):
        parts = sort.rsplit("_", 1)
        if len(parts) == 2 and parts[1] in ("asc", "desc"):
            sort = parts[0]
            order = parts[1]

    query = db.query(Paper)

    if search:
        query = query.filter(
            Paper.title.ilike(f"%{search}%")
            | Paper.authors.ilike(f"%{search}%")
            | (Paper.md_content.ilike(f"%{search}%") if Paper.md_content else False)
        )
    if status:
        query = query.filter(Paper.status == status)
    if year:
        query = query.filter(Paper.year == year)
    if tag:
        query = query.filter(Paper.tags.ilike(f"%{tag}%"))

    total = query.count()

    sort_col = getattr(Paper, sort, Paper.created_at)
    if order == "desc":
        sort_col = sort_col.desc()
    else:
        sort_col = sort_col.asc()

    papers = query.order_by(sort_col).offset((page - 1) * per_page).limit(per_page).all()

    return PaperListOut(
        items=[_paper_to_out(p) for p in papers],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/stats")
def get_paper_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Paper.id)).scalar()
    by_status = {}
    rows = db.query(Paper.status, func.count(Paper.id)).group_by(Paper.status).all()
    for status, count in rows:
        by_status[status] = count
    return {"total": total, "by_status": by_status}


@router.get("/{paper_id}", response_model=PaperDetail)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")

    return PaperDetail(
        id=paper.id,
        title=paper.title,
        filename=paper.filename,
        authors=paper.authors,
        venue=paper.venue,
        year=paper.year,
        tags=_parse_tags(paper.tags),
        status=paper.status,
        word_count=paper.word_count,
        page_count=paper.page_count,
        has_note=paper.note is not None,
        md_content=paper.md_content,
        md_path=paper.md_path,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
    )


@router.get("/{paper_id}/pdf")
def get_paper_pdf(paper_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper or not paper.pdf_path:
        raise HTTPException(404, "PDF not found")

    import os

    if not os.path.exists(paper.pdf_path):
        raise HTTPException(404, "PDF file missing on disk")

    return FileResponse(
        paper.pdf_path,
        media_type="application/pdf",
        filename=paper.filename,
    )


@router.put("/{paper_id}", response_model=PaperOut)
def update_paper(paper_id: int, data: PaperUpdate, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")

    update_data = data.model_dump(exclude_unset=True)
    if "tags" in update_data and update_data["tags"] is not None:
        update_data["tags"] = json.dumps(update_data["tags"], ensure_ascii=False)

    for key, value in update_data.items():
        setattr(paper, key, value)

    db.commit()
    db.refresh(paper)
    return _paper_to_out(paper)


@router.delete("/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")
    db.delete(paper)
    db.commit()
    return {"ok": True}
