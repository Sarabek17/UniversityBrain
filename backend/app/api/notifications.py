"""Notification endpoints. Thin layer: all logic lives in services/notifications.py.

    GET  /notifications[?unread=true&limit=]  -> the bell: rows + unread_count
    POST /notifications/{id}/read             -> mark one as read
    POST /notifications/read-all              -> mark everything as read

Scope needs no RBAC helper here: a notification belongs to exactly one person
(`Notification.user_id == user.id`). Somebody else's id answers **404** — the
documents/conversations rule, not 403: its existence is not disclosed either.

`GET` has a deliberate side effect (the S10 precedent): opening the bell first
runs the *computed* triggers — contract debt and execution deadlines — because
the hackathon build has no cron. Everything else is written by the action that
caused it.

Both POST endpoints answer with the refreshed list, so the bell needs no second
request to update its counter (the S8 `confirm` pattern).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.rbac import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import NotificationListOut, NotificationOut
from app.services import notifications as notifications_service

router = APIRouter(prefix="/notifications", tags=["notifications"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Bildirishnoma topilmadi"
)


def _list_out(feed: notifications_service.NotificationFeed) -> NotificationListOut:
    return NotificationListOut(
        rows=[NotificationOut.model_validate(row) for row in feed.rows],
        total=feed.total,
        unread_count=feed.unread_count,
        unread_only=feed.unread_only,
        limit=feed.limit,
    )


@router.get("", response_model=NotificationListOut)
def list_notifications(
    unread: bool = False,
    limit: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListOut:
    """Own notifications, newest first, with the unread counter included."""
    return _list_out(
        notifications_service.feed(db, user, unread_only=unread, limit=limit)
    )


@router.post("/read-all", response_model=NotificationListOut)
def read_all(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListOut:
    """"Hammasini o'qildi" — answers with the refreshed (all-read) list."""
    notifications_service.mark_all_read(db, user)
    return _list_out(notifications_service.feed(db, user, refresh=False))


@router.post("/{notification_id}/read", response_model=NotificationListOut)
def read_one(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListOut:
    """Mark one notification as read. Somebody else's id -> 404."""
    if notifications_service.mark_read(db, user, notification_id) is None:
        raise _NOT_FOUND
    return _list_out(notifications_service.feed(db, user, refresh=False))
