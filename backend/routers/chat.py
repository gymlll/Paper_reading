"""Chat router — paper Q&A with streaming support."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import get_db, SessionLocal
from backend.config import settings
from backend.models import Paper, ChatMessage
from backend.schemas import ChatRequest, ChatMessageOut

router = APIRouter()


@router.get("/papers/{paper_id}/messages", response_model=list[ChatMessageOut])
def get_chat_history(paper_id: int, db: Session = Depends(get_db)):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.paper_id == paper_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        ChatMessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            model_used=m.model_used,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/papers/{paper_id}/messages/stream")
def send_message_stream(
    paper_id: int,
    req: ChatRequest,
    db: Session = Depends(get_db),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")
    if not paper.md_content:
        raise HTTPException(400, "Paper has no content to chat about")

    # Save user message
    user_msg = ChatMessage(
        paper_id=paper_id,
        role="user",
        content=req.question,
    )
    db.add(user_msg)
    db.commit()

    # Resolve model
    provider, model = settings.resolve_model(None, None)
    model_key = f"{provider['id']}/{model['id']}"

    # Build messages list (capture paper content before generator runs)
    paper_content = paper.md_content[:50000]
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.paper_id == paper_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    import openai
    from backend.services.ai_service import CHAT_SYSTEM_PROMPT

    client = openai.OpenAI(
        api_key=provider["api_key"],
        base_url=provider["api_base"],
    )

    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT.format(
            paper_content=paper_content
        )},
    ]
    recent = history[-10:] if len(history) > 10 else history
    for msg in recent:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    model_id = model["id"]
    chat_max_tokens = settings.chat_max_tokens
    _paper_id = paper_id
    _model_key = model_key

    def event_stream():
        stream = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=chat_max_tokens,
            temperature=0.3,
            stream=True,
        )
        full_answer = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta:
                content = chunk.choices[0].delta.content or ""
                if content:
                    full_answer += content
                    yield content

        # Save full answer using a fresh DB session
        save_db = SessionLocal()
        try:
            assistant_msg = ChatMessage(
                paper_id=_paper_id,
                role="assistant",
                content=full_answer,
                model_used=_model_key,
            )
            save_db.add(assistant_msg)
            save_db.commit()
        finally:
            save_db.close()

    return StreamingResponse(event_stream(), media_type="text/plain")


@router.post("/papers/{paper_id}/messages", response_model=ChatMessageOut)
def send_message(
    paper_id: int,
    req: ChatRequest,
    db: Session = Depends(get_db),
):
    """Non-stream fallback — returns complete response."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(404, "Paper not found")
    if not paper.md_content:
        raise HTTPException(400, "Paper has no content to chat about")

    user_msg = ChatMessage(
        paper_id=paper_id,
        role="user",
        content=req.question,
    )
    db.add(user_msg)
    db.commit()

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.paper_id == paper_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    provider, model = settings.resolve_model(
        getattr(req, 'provider_id', None),
        getattr(req, 'model_id', None),
    )

    from backend.services.ai_service import chat_about_paper

    answer = chat_about_paper(paper.md_content, history, provider, model)

    model_key = f"{provider['id']}/{model['id']}"
    assistant_msg = ChatMessage(
        paper_id=paper_id,
        role="assistant",
        content=answer,
        model_used=model_key,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatMessageOut(
        id=assistant_msg.id,
        role=assistant_msg.role,
        content=assistant_msg.content,
        model_used=assistant_msg.model_used,
        created_at=assistant_msg.created_at,
    )


@router.delete("/papers/{paper_id}/messages")
def clear_chat_history(paper_id: int, db: Session = Depends(get_db)):
    db.query(ChatMessage).filter(ChatMessage.paper_id == paper_id).delete()
    db.commit()
    return {"ok": True}
