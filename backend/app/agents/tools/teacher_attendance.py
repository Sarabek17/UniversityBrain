"""`oqituvchi_davomat` — "which teachers did not show up today?" (dean's office).

The first tool in the project that is closed to the very role it reports on: a
teacher may not query their colleagues' attendance (FUNKSIONALLIK 3.8
"maxfiylik: o'qituvchi davomatini faqat dekanat/admin ko'radi"). That block is
in the registry, so the handler below is never called for a teacher — and it is
proven by a test, not by a prompt.

The wrapper only decides *what was asked*; the conclusion comes from
`services/presence.py`, the same code path the dean's page uses:

    no argument      -> today's roll-call, teachers needing attention first
    a name           -> that teacher's day (403-equivalent outside the scope)
    oy=true          -> monthly held/missed percentages
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.registry import Tool, ToolResult, register
from app.agents.tools.presence_check import parse_moment
from app.auth.rbac import can_access_user
from app.models import User, UserRole
from app.services import presence as presence_service

NAME = "oqituvchi_davomat"

MONTH_WORDS = {"1", "true", "ha", "oy", "oylik", "yes", "oyllik"}


def _find_teacher(db: Session, name: str) -> User | None:
    cleaned = name.strip()
    if not cleaned:
        return None
    query = db.query(User).filter(User.role == UserRole.teacher)
    return (
        query.filter(User.username.ilike(cleaned)).first()
        or query.filter(User.full_name.ilike(f"%{cleaned}%")).first()
    )


def handler(db: Session, user: User, args: dict) -> ToolResult:
    asked = str(args.get("oqituvchi") or args.get("o'qituvchi") or "").strip()
    period = str(args.get("davr") or "").strip().lower()
    moment = parse_moment(str(args.get("vaqt") or ""))

    if period in MONTH_WORDS:
        summary = presence_service.teacher_month_summary(db, user, now=moment)
        return ToolResult(
            text=presence_service.format_teacher_month_for_tool(summary),
            sources=[summary.source],
        )

    overview = presence_service.teacher_day_overview(db, user, now=moment)

    if not asked:
        return ToolResult(
            text=presence_service.format_teacher_overview_for_tool(overview),
            sources=[overview.source],
        )

    teacher = _find_teacher(db, asked)
    if teacher is None:
        return ToolResult(text=f"'{asked}' nomli o'qituvchi topilmadi.", ok=False)
    if not can_access_user(db, user, teacher):
        return ToolResult(
            text=(
                f"Ruxsat yo'q: {teacher.full_name} sizning fakultetingizga "
                "kirmaydi. Uning davomatini foydalanuvchiga bermang."
            ),
            ok=False,
        )
    row = next((r for r in overview.rows if r.teacher_id == teacher.id), None)
    if row is None:  # scope changed between the two queries — should not happen
        return ToolResult(
            text=f"{teacher.full_name} bo'yicha bugungi ma'lumot topilmadi.",
            ok=False,
        )
    return ToolResult(
        text=presence_service.format_teacher_row_for_tool(row, overview),
        sources=presence_service.teacher_row_sources(row, overview.date),
    )


register(
    Tool(
        name=NAME,
        description=(
            "O'qituvchilar davomati (faqat dekanat): bugun kim binoga kirgan, "
            "kimning darsi xavf ostida (dars vaqti keldi, o'qituvchi binoda "
            "emas), qaysi dars o'tildi, qayerda aniqlashtirish kerak. "
            "'Bugun kim darsga kelmadi?', 'Tursunovning darsi o'tdimi?', "
            "'oylik davomat foizi' kabi savollarda ishlat. Xona va dars vaqti "
            "— jadvalga asoslangan xulosa, javobda 'jadval bo'yicha' deb ayt; "
            "binoga kirish vaqti esa turniket logidan olingan fakt."
        ),
        parameters={
            "type": "object",
            "properties": {
                "oqituvchi": {
                    "type": "string",
                    "description": (
                        "Aniq o'qituvchi: ism yoki login. Bo'sh bo'lsa — "
                        "fakultetdagi barcha o'qituvchilar svodi."
                    ),
                },
                "davr": {
                    "type": "string",
                    "description": (
                        "'oy' bo'lsa — oxirgi 30 kunlik foizlar svodi. "
                        "Bo'sh bo'lsa — bugungi holat."
                    ),
                },
                "vaqt": {
                    "type": "string",
                    "description": (
                        "Qaysi payt holati: 'HH:MM' yoki ISO sana-vaqt. "
                        "Bo'sh bo'lsa — hozirgi vaqt."
                    ),
                },
            },
            "required": [],
        },
        handler=handler,
        # Only the dean's office (admin is always allowed by the registry).
        # teacher/tutor/student are blocked *before* the handler runs.
        roles=(UserRole.staff,),
    )
)
