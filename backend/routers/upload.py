"""Upload & parse router."""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import settings
from backend.models import Paper, BackgroundTask
from backend.schemas import UploadResponse, TaskOut

router = APIRouter()


@router.post("/pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    # Save uploaded PDF
    upload_dir = settings.uploads_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())[:8]
    safe_name = f"{file_id}_{file.filename}"
    pdf_path = upload_dir / safe_name

    content = await file.read()
    with open(pdf_path, "wb") as f:
        f.write(content)

    # Create paper record
    paper = Paper(
        title="",
        filename=file.filename,
        pdf_path=str(pdf_path),
        status="uploaded",
        source="upload",
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    # Create background task
    task_id = str(uuid.uuid4())
    task = BackgroundTask(
        id=task_id,
        task_type="mineru_parse",
        paper_id=paper.id,
        status="pending",
        progress=0,
        message="Waiting to start...",
    )
    db.add(task)
    db.commit()

    # Start background parsing
    from backend.services.mineru_service import start_mineru_parse

    start_mineru_parse(task_id, paper.id, str(pdf_path))

    return UploadResponse(paper_id=paper.id, task_id=task_id)


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    return TaskOut(
        id=task.id,
        task_type=task.task_type,
        paper_id=task.paper_id,
        status=task.status,
        progress=task.progress,
        message=task.message,
        result=task.result,
        error=task.error,
    )


@router.post("/papers/{paper_id}/full-pipeline", response_model=UploadResponse)
async def full_pipeline(
    paper_id: int,
    provider_id: str | None = None,
    model_id: str | None = None,
    db: Session = Depends(get_db),
):
    """One-click: parse + AI generate note."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")

    # Start parsing task (which will chain to AI note generation when done)
    task_id = str(uuid.uuid4())
    task = BackgroundTask(
        id=task_id,
        task_type="full_pipeline",
        paper_id=paper.id,
        status="pending",
        progress=0,
        message="Starting full pipeline...",
    )
    db.add(task)
    db.commit()

    from backend.services.mineru_service import start_full_pipeline

    start_full_pipeline(task_id, paper.id, paper.pdf_path, provider_id, model_id)

    return UploadResponse(paper_id=paper.id, task_id=task_id)
