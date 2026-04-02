"""MinerU API async service — wraps PDF parsing."""

import asyncio
import io
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
import zipfile

import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from backend.config import settings
from backend.database import SessionLocal
from backend.models import Paper, BackgroundTask


MINERU_API = "https://mineru.net/api/v4"


def start_mineru_parse(task_id: str, paper_id: int, pdf_path: str):
    """Launch background MinerU parsing task."""
    asyncio.ensure_future(_run_parse(task_id, paper_id, pdf_path))


def start_full_pipeline(
    task_id: str, paper_id: int, pdf_path: str,
    provider_id: str | None = None, model_id: str | None = None,
):
    """Launch full pipeline: parse + AI note generation."""
    asyncio.ensure_future(
        _run_full_pipeline(task_id, paper_id, pdf_path, provider_id, model_id)
    )


async def _update_task(task_id: str, **kwargs):
    db = SessionLocal()
    try:
        task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
        if task:
            for k, v in kwargs.items():
                setattr(task, k, v)
            db.commit()
    finally:
        db.close()


async def _update_paper(paper_id: int, **kwargs):
    db = SessionLocal()
    try:
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if paper:
            for k, v in kwargs.items():
                setattr(paper, k, v)
            db.commit()
    finally:
        db.close()


async def _run_parse(task_id: str, paper_id: int, pdf_path: str):
    token = settings.mineru_token
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    filename = os.path.basename(pdf_path)

    try:
        await _update_task(task_id, status="running", progress=5, message="Requesting upload URL...")
        await _update_paper(paper_id, status="parsing")

        # Step 1: Get upload URL
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{MINERU_API}/file-urls/batch",
                headers=headers,
                json={
                    "files": [{"name": filename}],
                    "model_version": settings.mineru_model_version,
                    "enable_formula": settings.mineru_enable_formula,
                    "enable_table": settings.mineru_enable_table,
                    "language": settings.mineru_language,
                },
            )
            result = resp.json()

        if result["code"] != 0:
            raise Exception(f"Get upload URL failed: {result['msg']}")

        batch_id = result["data"]["batch_id"]
        upload_url = result["data"]["file_urls"][0]

        await _update_task(task_id, progress=15, message=f"Uploading {filename}...")
        await _update_paper(paper_id, mineru_batch_id=batch_id)

        # Step 2: Upload file
        async with httpx.AsyncClient(timeout=120) as client:
            with open(pdf_path, "rb") as f:
                put_resp = await client.put(upload_url, content=f.read())
            if put_resp.status_code not in (200, 201):
                raise Exception(f"Upload failed: HTTP {put_resp.status_code}")

        # Step 3: Poll for result
        await _update_task(task_id, progress=25, message="Waiting for MinerU to parse...")

        poll_url = f"{MINERU_API}/extract-results/batch/{batch_id}"
        timeout = settings.mineru_poll_timeout
        interval = settings.mineru_poll_interval
        elapsed = 0
        consecutive_errors = 0

        while elapsed < timeout:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(poll_url, headers=headers)
                result = resp.json()
                consecutive_errors = 0

                for item in result["data"]["extract_result"]:
                    state = item["state"]

                    if state == "done":
                        zip_url = item["full_zip_url"]
                        await _update_task(task_id, progress=80, message="Downloading result...")
                        await _download_and_save(task_id, paper_id, zip_url)
                        return

                    if state == "failed":
                        raise Exception(f"Parse failed: {item.get('err_msg', 'Unknown')}")

                    progress_data = item.get("extract_progress")
                    if progress_data:
                        extracted = progress_data.get("extracted_pages", "?")
                        total = progress_data.get("total_pages", "?")
                        pct = 25 + int(50 * extracted / total) if isinstance(extracted, int) and isinstance(total, int) and total > 0 else 50
                        await _update_task(
                            task_id,
                            progress=pct,
                            message=f"Parsing: {extracted}/{total} pages",
                        )

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                consecutive_errors += 1
                if consecutive_errors >= 10:
                    raise Exception(f"Too many network errors: {e}")

            await asyncio.sleep(interval)
            elapsed += interval

        raise Exception(f"Timeout after {timeout}s")

    except Exception as e:
        logger.exception("Parse failed for task %s paper %s", task_id, paper_id)
        await _update_task(task_id, status="failed", error=str(e), message=str(e))
        await _update_paper(paper_id, status="error")


async def _download_zip(zip_url: str) -> bytes:
    """Download zip from MinerU CDN.

    The MinerU CDN requires SSL renegotiation that Python's ssl module
    cannot handle on Windows. We use curl (which uses schannel) instead.
    Falls back to httpx on non-Windows or when curl is unavailable.
    """
    if shutil.which("curl"):
        # Use curl — handles SSL renegotiation via OS-native schannel
        tmp = tempfile.mktemp(suffix=".zip")
        try:
            proc = await asyncio.create_subprocess_exec(
                "curl", "-L", "-s", "-o", tmp, "--connect-timeout", "30",
                zip_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.wait(), timeout=120)
            if proc.returncode != 0:
                raise Exception(f"curl exited with code {proc.returncode}")
            with open(tmp, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    else:
        # Fallback: try httpx (may fail on Windows with certain CDN SSL)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=15.0),
            follow_redirects=True,
        ) as client:
            resp = await client.get(zip_url)
            resp.raise_for_status()
            return resp.content


import re


def _extract_metadata(paper: Paper, md_content: str):
    """Extract title, authors, year, venue from parsed markdown."""
    # Only fill if fields are empty
    if paper.title and paper.authors:
        return

    lines = md_content.split("\n")

    # Title: first non-empty line that looks like a heading or plain text
    title = ""
    for line in lines[:30]:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip image/link-only lines and preprint notices
        if stripped.startswith("!") or stripped.startswith("["):
            continue
        if any(
            kw in stripped.lower()
            for kw in ["preprint", "under review", "do not redistribute", "copyright"]
        ):
            continue
        # Remove leading # marks
        cleaned = re.sub(r"^#+\s*", "", stripped).strip()
        # Must be reasonably long but not too long (not a paragraph)
        if 10 < len(cleaned) < 300:
            title = cleaned
            break

    if title:
        paper.title = title[:500]

    # Authors: look for lines after title that contain comma-separated names
    authors = ""
    title_found = False
    for line in lines[:40]:
        stripped = line.strip()
        if not stripped:
            continue
        cleaned = re.sub(r"^#+\s*", "", stripped).strip()
        if cleaned == paper.title:
            title_found = True
            continue
        if title_found and not authors:
            if "," in stripped and len(stripped) < 500:
                author_line = re.sub(
                    r"^(authors?|by)\s*:\s*", "", stripped, flags=re.IGNORECASE
                )
                # Remove LaTeX math, superscripts, affiliations
                author_line = re.sub(r"\$[^$]+\$", "", author_line)
                author_line = re.sub(r"[\{\}\\\\]", "", author_line)
                author_line = re.sub(r"\s*\d+\s*(?=,|$)", "", author_line)
                author_line = re.sub(r"\s*,\s*$", "", author_line)
                if not any(
                    kw in author_line.lower()
                    for kw in [
                        "abstract", "introduction", "university", "department",
                        "preprint", "review",
                    ]
                ):
                    authors = author_line.strip()
                    break

    if authors:
        paper.authors = authors[:1000]

    # Year: look for 4-digit year in first 2000 chars
    year_match = re.search(r"\b(19|20)\d{2}\b", md_content[:2000])
    if year_match and not paper.year:
        paper.year = int(year_match.group())

    # Venue: look for known conference/journal abbreviations
    venue_abbrs = [
        "ACL", "EMNLP", "NeurIPS", "NIPS", "ICML", "ICLR", "AAAI", "IJCAI",
        "CVPR", "ICCV", "ECCV", "SIGIR", "KDD", "WWW", "WSDM", "CIKM",
        "NAACL", "COLING", "TACL", "JMLR", "TOIS", "TACO", "ACL-IJCNLP",
    ]
    if not paper.venue:
        # Look for "published in/in Proceedings of" pattern
        m = re.search(
            r"(?:published\s+in|proceedings\s+of)\s+([^\n,.]{5,80})",
            md_content[:3000],
            re.IGNORECASE,
        )
        if m:
            paper.venue = m.group(1).strip()[:200]
        else:
            # Look for known abbreviations as whole words
            for abbr in venue_abbrs:
                if re.search(r"\b" + abbr + r"\b", md_content[:3000]):
                    paper.venue = abbr
                    break


async def _download_and_save(task_id: str, paper_id: int, zip_url: str):
    # MinerU CDN uses SSL renegotiation incompatible with Python's ssl module.
    # Fall back to curl (Windows schannel / system SSL) for downloading.
    zip_data = await _download_zip(zip_url)

    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        md_files = [f for f in z.namelist() if f.endswith("full.md")]
        if not md_files:
            # Try plain .md files as fallback
            md_files = [f for f in z.namelist() if f.endswith(".md") and "/" not in f]
        if not md_files:
            raise Exception(f"No markdown file in zip. Contents: {z.namelist()}")

        md_content = z.read(md_files[0]).decode("utf-8")

    # Save to papers/ directory
    db = SessionLocal()
    try:
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        safe_name = os.path.splitext(paper.filename)[0] + ".md"
        md_path = settings.papers_dir / safe_name

        settings.papers_dir.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_content, encoding="utf-8")

        paper.md_path = str(md_path)
        paper.md_content = md_content
        paper.status = "parsed"
        paper.word_count = len(md_content)

        # Extract metadata from markdown content
        _extract_metadata(paper, md_content)

        task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
        task.status = "done"
        task.progress = 100
        task.message = "Parsing complete"
        task.result = json.dumps({"md_path": str(md_path), "word_count": len(md_content)})

        db.commit()
    finally:
        db.close()


async def _run_full_pipeline(
    task_id: str, paper_id: int, pdf_path: str,
    provider_id: str | None, model_id: str | None,
):
    """Full pipeline: MinerU parse → AI note generation."""
    try:
        # Phase 1: Parse
        await _update_task(task_id, status="running", progress=0, message="Phase 1: Parsing PDF...")
        await _run_parse_inner(task_id, paper_id, pdf_path)

        # Phase 2: Generate note
        await _update_task(task_id, progress=85, message="Phase 2: Generating AI note...")

        from backend.services.ai_service import generate_note_sync

        generate_note_sync(paper_id, provider_id, model_id)

        await _update_task(task_id, status="done", progress=100, message="Full pipeline complete!")

    except Exception as e:
        await _update_task(task_id, status="failed", error=str(e), message=str(e))


async def _run_parse_inner(task_id: str, paper_id: int, pdf_path: str):
    """Internal parse (used by full pipeline to avoid nested task creation)."""
    token = settings.mineru_token
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    filename = os.path.basename(pdf_path)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{MINERU_API}/file-urls/batch",
            headers=headers,
            json={
                "files": [{"name": filename}],
                "model_version": settings.mineru_model_version,
                "enable_formula": settings.mineru_enable_formula,
                "enable_table": settings.mineru_enable_table,
                "language": settings.mineru_language,
            },
        )
        result = resp.json()

    if result["code"] != 0:
        raise Exception(f"Get upload URL failed: {result['msg']}")

    batch_id = result["data"]["batch_id"]
    upload_url = result["data"]["file_urls"][0]

    async with httpx.AsyncClient(timeout=120) as client:
        with open(pdf_path, "rb") as f:
            put_resp = await client.put(upload_url, content=f.read())

    poll_url = f"{MINERU_API}/extract-results/batch/{batch_id}"
    timeout = settings.mineru_poll_timeout
    interval = settings.mineru_poll_interval
    elapsed = 0

    while elapsed < timeout:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(poll_url, headers=headers)
            result = resp.json()

            for item in result["data"]["extract_result"]:
                if item["state"] == "done":
                    await _download_and_save(task_id, paper_id, item["full_zip_url"])
                    return
                if item["state"] == "failed":
                    raise Exception(f"Parse failed: {item.get('err_msg')}")
        except (httpx.ConnectError, httpx.TimeoutException):
            pass

        await asyncio.sleep(interval)
        elapsed += interval

    raise Exception(f"MinerU timeout after {timeout}s")
