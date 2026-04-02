"""AI service — LLM integration for note generation and chat."""

import asyncio

import openai
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.models import Paper, Note, BackgroundTask, ChatMessage


NOTE_SYSTEM_PROMPT = """你是一个学术论文阅读助手。你的任务是根据论文全文，生成一篇结构化的阅读笔记。

请严格按照以下模板格式输出（用中文撰写，专业术语保留英文）：

# {论文标题}

## 基本信息

| 项目 | 内容 |
|------|------|
| 标题 | {从论文提取} |
| 作者 | {从论文提取} |
| 会议/期刊 | {从论文提取} |
| 年份 | {从论文提取} |
| 领域标签 | {自动生成} |
| 阅读日期 | {今天} |

## 一句话总结

> 用一句话概括这篇论文解决了什么问题、用了什么方法、得到了什么结果。

## 研究背景与动机

- 解决什么问题？
- 为什么这个问题重要？
- 之前的方法有什么不足？

## 核心方法

- 方法概述
- 关键创新点
- 重要公式或模型结构（如有）

## 实验结果

- 数据集与评估指标
- 主要实验结论
- 与前人工作的对比

## 亮点

1. {具体亮点}
2. {具体亮点}
3. {具体亮点}

## 缺陷与局限

1. {具体缺陷}
2. {具体缺陷}
3. {具体缺陷}

## 启发与思考

- 对自己研究的启发：
- 可能的延伸方向：
- 值得借鉴的写作手法：

## 关键图表

（记录论文中最关键的图表及其含义）

## 引用信息

```
BibTeX 引用
```

要求：
- 一句话总结控制在50字以内
- 亮点和缺陷要具体，不要泛泛而谈
- BibTeX 根据论文中的信息生成
"""

CHAT_SYSTEM_PROMPT = """你是一个专业的学术论文阅读助手。用户正在阅读一篇学术论文，你可以基于论文内容回答他们的问题。

规则：
1. 回答必须基于论文内容，不要编造论文中没有的信息
2. 如果论文中没有足够信息回答问题，请如实说明
3. 回答使用中文，专业术语保留英文
4. 回答要具体、有针对性，引用论文中的关键内容
5. 如果用户问的是你自己的观点，可以基于论文内容给出分析

以下是论文全文内容：

{paper_content}
"""

PRESET_QUESTIONS = [
    "这篇论文的主要贡献是什么？",
    "方法有什么局限性？",
    "核心方法是什么？",
    "对我的研究有什么启发？",
]


def start_ai_note_generation(
    task_id: str, paper_id: int,
    provider_id: str | None = None, model_id: str | None = None,
):
    """Launch AI note generation as background task."""
    asyncio.ensure_future(
        _run_ai_note_generation(task_id, paper_id, provider_id, model_id)
    )


def generate_note_sync(
    paper_id: int,
    provider_id: str | None = None,
    model_id: str | None = None,
):
    """Synchronous note generation (used by full pipeline)."""
    db = SessionLocal()
    try:
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper or not paper.md_content:
            raise Exception("Paper not found or no content")

        provider, model = settings.resolve_model(provider_id, model_id)

        client = openai.OpenAI(
            api_key=provider["api_key"],
            base_url=provider["api_base"],
        )

        # Truncate if too long
        content = paper.md_content[:60000]

        response = client.chat.completions.create(
            model=model["id"],
            messages=[
                {"role": "system", "content": NOTE_SYSTEM_PROMPT},
                {"role": "user", "content": f"请为以下论文生成结构化阅读笔记：\n\n{content}"},
            ],
            max_tokens=settings.note_max_tokens,
            temperature=settings.temperature,
        )

        note_content = response.choices[0].message.content

        # Extract summary
        summary = ""
        for line in note_content.splitlines():
            if line.startswith("> ") and "总结" in note_content[:500]:
                summary = line[2:].strip()
                break

        # Delete existing note if any
        existing = db.query(Note).filter(Note.paper_id == paper_id).first()
        if existing:
            db.delete(existing)

        note = Note(
            paper_id=paper_id,
            content=note_content,
            summary=summary,
            is_ai_generated=1,
            ai_model_used=f"{provider['id']}/{model['id']}",
        )
        db.add(note)
        paper.status = "noted"
        db.commit()

    finally:
        db.close()


async def _run_ai_note_generation(
    task_id: str, paper_id: int,
    provider_id: str | None, model_id: str | None,
):
    db = SessionLocal()
    try:
        task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
        task.status = "running"
        task.progress = 10
        task.message = "Generating note with AI..."
        db.commit()
    finally:
        db.close()

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: generate_note_sync(paper_id, provider_id, model_id),
        )

        db = SessionLocal()
        task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
        task.status = "done"
        task.progress = 100
        task.message = "Note generated successfully"
        db.commit()
        db.close()

    except Exception as e:
        db = SessionLocal()
        task = db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.error = str(e)
            task.message = str(e)
            db.commit()
        db.close()


def chat_about_paper(
    paper_content: str,
    history: list,
    provider: dict,
    model: dict,
) -> str:
    """Synchronous chat completion for paper Q&A.

    Args:
        paper_content: Full markdown content of the paper
        history: List of ChatMessage ORM objects
        provider: provider config dict with 'api_key' and 'api_base'
        model: model config dict with 'id'
    """
    client = openai.OpenAI(
        api_key=provider["api_key"],
        base_url=provider["api_base"],
    )

    # Build messages
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT.format(
            paper_content=paper_content[:50000]
        )},
    ]

    # Add history (keep last 10 messages)
    recent = history[-10:] if len(history) > 10 else history
    for msg in recent:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    response = client.chat.completions.create(
        model=model["id"],
        messages=messages,
        max_tokens=settings.chat_max_tokens,
        temperature=0.3,
    )

    return response.choices[0].message.content
