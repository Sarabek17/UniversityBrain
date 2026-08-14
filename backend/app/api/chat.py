"""Chat endpoints. Thin layer: the whole flow lives in agents/orchestrator.py.

    POST /chat                        -> answer + sources + disclaimer
    GET  /chat/conversations          -> own conversations
    GET  /chat/conversations/{id}     -> own conversation with its messages

RBAC: every authenticated role may chat (the tools decide what they can see);
a conversation is only ever readable by its owner.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agents import orchestrator
from app.auth.rbac import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import (
    ChatIn,
    ChatOut,
    ConversationDetailOut,
    ConversationOut,
)

router = APIRouter(prefix="/chat", tags=["chat"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Suhbat topilmadi"
)


@router.post("", response_model=ChatOut)
def chat(
    body: ChatIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatOut:
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Xabar bo'sh bo'lishi mumkin emas",
        )

    if body.conversation_id is None:
        conversation = orchestrator.create_conversation(db, user, message)
    else:
        conversation = orchestrator.get_conversation(db, user, body.conversation_id)
        if conversation is None:
            raise _NOT_FOUND

    answer = orchestrator.run_chat(db, user, conversation, message)
    return ChatOut(
        conversation_id=conversation.id,
        text=answer.text,
        sources=answer.sources,
        disclaimer=answer.disclaimer,
    )


@router.get("/conversations", response_model=list[ConversationOut])
def conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationOut]:
    return orchestrator.list_conversations(db, user)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def conversation_detail(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetailOut:
    conversation = orchestrator.get_conversation(db, user, conversation_id)
    if conversation is None:
        # 404 rather than 403: another user's conversation must not be probeable.
        raise _NOT_FOUND
    return conversation
