"""`bildirishnomalar` — "menda yangi nima bor?" (FUNKSIONALLIK 3.10).

The wrapper only decides *how much* to show; the answer comes from
`services/notifications.py`, the very code path the bell renders — including
the computed triggers (contract debt, execution deadlines), so the agent and
the bell can never disagree.

Permission has two layers (domain rule 2), the `ariza_holati` pattern:
    1. the registry lets every role call the tool — everyone has a bell,
    2. the data layer answers with `Notification.user_id == user.id` only, so
       nobody ever sees another person's notifications.

The answer always opens with the mandatory citation (domain rule 5):
"Bildirishnomalar ro'yxati, 15.08.2026 (3 ta o'qilmagan)".
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.registry import ALL_ROLES, Tool, ToolResult, register
from app.models import User
from app.services import notifications as notifications_service

NAME = "bildirishnomalar"

ALL_WORDS = {"hammasi", "barchasi", "all", "oqilgan", "o'qilgan"}


def handler(db: Session, user: User, args: dict) -> ToolResult:
    raw = str(args.get("holat") or args.get("turi") or "").strip().lower()
    unread_only = raw not in ALL_WORDS

    limit = args.get("nechta")
    try:
        limit = int(limit) if limit is not None else None
    except (TypeError, ValueError):
        limit = None

    feed = notifications_service.feed(
        db, user, unread_only=unread_only, limit=limit
    )
    return ToolResult(
        text=notifications_service.format_feed_for_tool(feed),
        sources=[feed.source],
    )


register(
    Tool(
        name=NAME,
        description=(
            "Foydalanuvchining bildirishnomalarini (qo'ng'iroqcha) qaytaradi: "
            "o'qilmaganlar svodi — ariza holati o'zgardi, yangi hujjat keldi, "
            "ijro muddati yaqin, to'lov cheki/qarzdorlik, darsga kelmadingiz, "
            "dars xavf ostida. 'Menda yangi nima bor?', 'bildirishnomalarim', "
            "'nima o'zgardi?' kabi savollarda ishlat. Javobda ro'yxatning "
            "birinchi qatorini manba sifatida keltir."
        ),
        parameters={
            "type": "object",
            "properties": {
                "holat": {
                    "type": "string",
                    "description": (
                        "Bo'sh yoki 'oqilmagan' — faqat o'qilmaganlar "
                        "(standart); 'hammasi' — o'qilganlar bilan birga."
                    ),
                },
                "nechta": {
                    "type": "integer",
                    "description": "Nechta bildirishnoma ko'rsatilsin (standart 30).",
                },
            },
            "required": [],
        },
        handler=handler,
        # Open to every role: the restriction is in the data layer
        # (`Notification.user_id == user.id`), not in the tool list.
        roles=ALL_ROLES,
    )
)
