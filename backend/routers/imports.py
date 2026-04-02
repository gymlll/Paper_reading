"""Import existing papers and notes into database."""

import json
import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import settings
from backend.models import Paper, Note

router = APIRouter()


@router.post("/existing")
def import_existing(db: Session = Depends(get_db)):
    """Scan papers/ and notes/ directories and import into DB."""
    imported_papers = 0
    imported_notes = 0
    skipped = 0

    # Import from papers/ directory
    papers_dir = settings.papers_dir
    if papers_dir.exists():
        for md_file in papers_dir.glob("*.md"):
            # Check if already imported by filename
            filename = md_file.stem + ".pdf"
            existing = db.query(Paper).filter(Paper.filename == filename).first()
            if existing:
                skipped += 1
                continue

            content = md_file.read_text(encoding="utf-8")

            # Extract title from first H1
            title = md_file.stem
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

            paper = Paper(
                title=title,
                filename=filename,
                md_path=str(md_file),
                md_content=content,
                status="parsed",
                source="import",
                word_count=len(content),
            )
            db.add(paper)
            imported_papers += 1

    db.commit()

    # Import from notes/ directory
    notes_dir = settings.notes_dir
    if notes_dir.exists():
        for md_file in notes_dir.glob("*.md"):
            if md_file.name == "_template.md":
                continue

            content = md_file.read_text(encoding="utf-8")

            # Try to match to a paper by filename pattern
            stem = md_file.stem
            matched_paper = None

            # Try matching: author_year_keyword -> find paper
            # Simple heuristic: search for similar title
            all_papers = db.query(Paper).all()
            for p in all_papers:
                note_name = stem.lower().replace("_", " ")
                paper_title = (p.title or "").lower()
                if any(word in paper_title for word in note_name.split() if len(word) > 3):
                    matched_paper = p
                    break

            if not matched_paper:
                skipped += 1
                continue

            if matched_paper.note:
                skipped += 1
                continue

            # Extract summary
            summary = ""
            for line in content.splitlines():
                if line.startswith("> ") and "总结" in content[:content.find(line) + 100]:
                    summary = line[2:].strip()
                    break

            note = Note(
                paper_id=matched_paper.id,
                content=content,
                summary=summary,
                is_ai_generated=1,
                ai_model_used="claude-code",
            )
            db.add(note)
            imported_notes += 1

    db.commit()

    return {
        "imported_papers": imported_papers,
        "imported_notes": imported_notes,
        "skipped": skipped,
    }
