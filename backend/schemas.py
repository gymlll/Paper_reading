"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# --- Papers ---

class PaperCreate(BaseModel):
    title: Optional[str] = ""
    authors: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[int] = None
    tags: Optional[list[str]] = None


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[int] = None
    tags: Optional[list[str]] = None


class PaperOut(BaseModel):
    id: int
    title: str
    filename: str
    authors: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[int] = None
    tags: Optional[list[str]] = None
    status: str
    word_count: Optional[int] = None
    page_count: Optional[int] = None
    has_note: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaperDetail(PaperOut):
    md_content: Optional[str] = None
    md_path: Optional[str] = None


class PaperListOut(BaseModel):
    items: list[PaperOut]
    total: int
    page: int
    per_page: int


# --- Notes ---

class NoteCreate(BaseModel):
    content: str = ""
    summary: Optional[str] = None
    highlights: Optional[list[str]] = None
    tags: Optional[list[str]] = None


class NoteUpdate(BaseModel):
    content: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    bibtex: Optional[str] = None


class NoteOut(BaseModel):
    id: int
    paper_id: int
    content: str
    summary: Optional[str] = None
    highlights: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    bibtex: Optional[str] = None
    ai_model_used: Optional[str] = None
    is_ai_generated: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Chat ---

class ChatRequest(BaseModel):
    question: str
    provider_id: Optional[str] = None
    model_id: Optional[str] = None


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    model_used: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- Background Tasks ---

class TaskOut(BaseModel):
    id: str
    task_type: str
    paper_id: Optional[int] = None
    status: str
    progress: int
    message: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Settings / Providers ---

class ModelInProvider(BaseModel):
    id: str
    name: Optional[str] = None
    is_default: bool = False


class ProviderCreate(BaseModel):
    id: str
    name: str
    api_base: str
    api_key: str
    models: list[ModelInProvider] = []
    enabled: bool = True


class ProviderOut(BaseModel):
    id: str
    name: str
    api_base: str
    api_key_masked: str  # only last 4 chars
    models: list[dict]
    enabled: bool


class ModelOut(BaseModel):
    provider_id: str
    provider_name: str
    model_id: str
    model_name: str
    is_default: bool


# --- Dashboard ---

class DashboardStats(BaseModel):
    total_papers: int
    papers_this_month: int
    ai_notes_count: int
    pending_papers: int


class RecentPaper(BaseModel):
    id: int
    title: str
    status: str
    has_note: bool
    created_at: Optional[datetime] = None


class DashboardData(BaseModel):
    stats: DashboardStats
    recent_papers: list[RecentPaper]


# --- Upload ---

class UploadResponse(BaseModel):
    paper_id: int
    task_id: str


# --- AI Generate ---

class GenerateNoteRequest(BaseModel):
    provider_id: Optional[str] = None
    model_id: Optional[str] = None


class FullPipelineRequest(BaseModel):
    provider_id: Optional[str] = None
    model_id: Optional[str] = None
