"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    Text,
    String,
    ForeignKey,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False, default="")
    filename = Column(Text, nullable=False)
    pdf_path = Column(Text, nullable=True)
    md_path = Column(Text, nullable=True)
    md_content = Column(Text, nullable=True)
    authors = Column(Text, nullable=True)
    venue = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array string
    status = Column(String(20), nullable=False, default="uploaded")
    mineru_batch_id = Column(Text, nullable=True)
    source = Column(String(20), nullable=False, default="upload")
    word_count = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    note = relationship("Note", back_populates="paper", uselist=False, cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="paper", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, unique=True)
    content = Column(Text, nullable=False, default="")
    summary = Column(Text, nullable=True)
    highlights = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    bibtex = Column(Text, nullable=True)
    ai_model_used = Column(Text, nullable=True)
    is_ai_generated = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    paper = relationship("Paper", back_populates="note")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    model_used = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    paper = relationship("Paper", back_populates="chat_messages")


class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id = Column(Text, primary_key=True)
    task_type = Column(String(30), nullable=False)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    progress = Column(Integer, nullable=False, default=0)
    message = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

