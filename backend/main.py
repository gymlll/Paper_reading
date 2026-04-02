"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.papers_dir.mkdir(parents=True, exist_ok=True)
    settings.notes_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] {settings.app_name} started")
    print(f"[*] Database: {settings.database_path}")
    print(f"[*] LLM providers: {[p['id'] for p in settings.llm_providers]}")
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and mount routers
from backend.routers import papers, dashboard, upload, notes, chat, settings as settings_router, imports  # noqa: E402

app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(papers.router, prefix="/api/v1/papers", tags=["papers"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])
app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(imports.router, prefix="/api/v1/import", tags=["import"])


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}
