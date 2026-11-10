"""
AI Analyst Router — Gemini-powered security analyst chatbot.
Supports multi-turn conversations with optional context (alert/threat/log).
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_org_id, rate_limit
from app.models.ai_conversation import AIConversation
from app.models.user import User
from app.schemas.schemas import AIMessage, AIResponse
from app.services.ai_service import get_ai_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=AIResponse, dependencies=[Depends(rate_limit)])
async def chat_with_analyst(
    payload: AIMessage,
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Sends a message to the AI security analyst and returns a response.
    Creates or continues an existing conversation session.
    """
    session_id = payload.session_id or str(uuid.uuid4())

    # Load or create conversation
    result = await db.execute(
        select(AIConversation).where(
            AIConversation.session_id == session_id,
            AIConversation.org_id == org_id,
            AIConversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = AIConversation(
            org_id=org_id,
            user_id=current_user.id,
            session_id=session_id,
            messages=[],
            context_type=payload.context_type,
            context_ref_id=payload.context_ref_id,
        )
        db.add(conversation)

    # Append user message
    user_msg = {
        "role": "user",
        "content": payload.content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    conversation.messages = list(conversation.messages) + [user_msg]

    # Get AI response
    ai_text, tokens_used = await get_ai_response(
        user_message=payload.content,
        history=conversation.messages[:-1],  # Exclude the message just added
        context_type=payload.context_type,
        context_ref_id=payload.context_ref_id,
    )

    # Append AI response
    ai_msg = {
        "role": "assistant",
        "content": ai_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    conversation.messages = list(conversation.messages) + [ai_msg]
    conversation.title = payload.content[:100] if len(conversation.messages) <= 2 else conversation.title
    await db.flush()

    return AIResponse(
        session_id=session_id,
        message=ai_text,
        timestamp=datetime.now(timezone.utc),
        tokens_used=tokens_used,
    )


@router.get("/conversations", dependencies=[Depends(rate_limit)])
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Lists the current user's conversation sessions."""
    result = await db.execute(
        select(AIConversation)
        .where(AIConversation.user_id == current_user.id, AIConversation.org_id == org_id)
        .order_by(AIConversation.updated_at.desc())
        .limit(50)
    )
    convs = result.scalars().all()
    return [{"session_id": c.session_id, "title": c.title, "updated_at": c.updated_at} for c in convs]


@router.get("/conversations/{session_id}", dependencies=[Depends(rate_limit)])
async def get_conversation(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    org_id = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns all messages in a conversation session."""
    result = await db.execute(
        select(AIConversation).where(
            AIConversation.session_id == session_id,
            AIConversation.org_id == org_id,
            AIConversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return {"session_id": conv.session_id, "messages": conv.messages}
