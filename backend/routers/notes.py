"""Notes router — CRUD + AI generation."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Paper, Note, BackgroundTask
from backend.schemas import NoteCreate, NoteUpdate, NoteOut, GenerateNoteRequest, TaskOut

router = APIRouter()


@router.get("/papers/{paper_id}/note", response_model=NoteOut)
def get_note(paper_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.paper_id == paper_id).first()
    if not note:
        raise HTTPException(404, "Note not found")
    return _note_to_out(note)


@router.post("/papers/{paper_id}/note", response_model=NoteOut)
def create_note(paper_id: int, data: NoteCreate, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")
    if paper.note:
        raise HTTPException(400, "Note already exists. Use PUT to update.")

    note = Note(
        paper_id=paper_id,
        content=data.content,
        summary=data.summary,
        highlights=json.dumps(data.highlights, ensure_ascii=False) if data.highlights else None,
        tags=json.dumps(data.tags, ensure_ascii=False) if data.tags else None,
        is_ai_generated=0,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_to_out(note)


@router.put("/{note_id}", response_model=NoteOut)
def update_note(note_id: int, data: NoteUpdate, db: Session = Depends(get_db)):
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(404, "Note not found")

    update_data = data.model_dump(exclude_unset=True)
    if "highlights" in update_data and update_data["highlights"] is not None:
        update_data["highlights"] = json.dumps(update_data["highlights"], ensure_ascii=False)
    if "tags" in update_data and update_data["tags"] is not None:
        update_data["tags"] = json.dumps(update_data["tags"], ensure_ascii=False)

    # If AI-generated note is edited, mark as AI+edit
    if note.is_ai_generated == 1 and "content" in update_data:
        update_data["is_ai_generated"] = 2

    for key, value in update_data.items():
        setattr(note, key, value)

    db.commit()
    db.refresh(note)
    return _note_to_out(note)


@router.post("/papers/{paper_id}/generate-note", response_model=TaskOut)
async def generate_note(
    paper_id: int,
    req: GenerateNoteRequest,
    db: Session = Depends(get_db),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")
    if not paper.md_content:
        raise HTTPException(400, "Paper has no parsed content. Run MinerU first.")

    task_id = str(uuid.uuid4())
    task = BackgroundTask(
        id=task_id,
        task_type="ai_generate_note",
        paper_id=paper.id,
        status="pending",
        progress=0,
        message="Queuing AI note generation...",
    )
    db.add(task)
    db.commit()

    import asyncio
    from backend.services.ai_service import _run_ai_note_generation

    asyncio.create_task(
        _run_ai_note_generation(task_id, paper.id, req.provider_id, req.model_id)
    )

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


def _note_to_out(note: Note) -> NoteOut:
    return NoteOut(
        id=note.id,
        paper_id=note.paper_id,
        content=note.content,
        summary=note.summary,
        highlights=json.loads(note.highlights) if note.highlights else None,
        tags=json.loads(note.tags) if note.tags else None,
        bibtex=note.bibtex,
        ai_model_used=note.ai_model_used,
        is_ai_generated=note.is_ai_generated,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )
