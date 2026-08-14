"""`davomat_kor` — attendance figures, always inside the caller's scope.

Who gets what when no name is given:
    student            -> their own attendance over the last N days
    teacher            -> their own classes today: marked / not marked yet
    tutor / staff      -> the presence + attendance summary of their groups
    admin              -> the same, unrestricted

With a name it is always one student, and `can_access_user` decides whether
that student is inside the caller's scope (a tutor of another faculty is
refused, a student asking about a group mate is refused).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.registry import ALL_ROLES, Tool, ToolResult, register
from app.auth.rbac import can_access_user
from app.models import User, UserRole
from app.services import presence as presence_service

NAME = "davomat_kor"

SELF_WORDS = {"men", "o'zim", "ozim", "menda", "o'zimni"}


def _find_student(db: Session, name: str) -> User | None:
    cleaned = name.strip()
    if not cleaned:
        return None
    query = db.query(User).filter(User.role == UserRole.student)
    return (
        query.filter(User.username.ilike(cleaned)).first()
        or query.filter(User.full_name.ilike(f"%{cleaned}%")).first()
    )


def _days(args: dict) -> int:
    raw = args.get("kunlar")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return presence_service.DEFAULT_SUMMARY_DAYS


def _student_summary(db: Session, student: User, days: int) -> ToolResult:
    summary = presence_service.attendance_summary(db, student, days)
    return ToolResult(
        text=presence_service.format_attendance_for_tool(summary),
        sources=[summary.source],
    )


def handler(db: Session, user: User, args: dict) -> ToolResult:
    asked = str(args.get("talaba") or "").strip()
    days = _days(args)

    if user.role == UserRole.student:
        if asked and asked.lower() not in (
            SELF_WORDS | {user.username.lower(), user.full_name.lower()}
        ):
            other = _find_student(db, asked)
            if other is None or other.id != user.id:
                return ToolResult(
                    text=(
                        f"Ruxsat yo'q: '{asked}' ning davomati sizga ochiq emas. "
                        "Talaba faqat o'z davomatini ko'ra oladi — "
                        "foydalanuvchiga shuni ayting."
                    ),
                    ok=False,
                )
        return _student_summary(db, user, days)

    if not asked or asked.lower() in SELF_WORDS:
        if user.role == UserRole.teacher:
            now = datetime.now()
            classes = presence_service.teacher_classes(db, user, now.date(), now)
            return ToolResult(
                text=presence_service.format_teacher_day_for_tool(
                    classes, user, now.date()
                ),
                sources=[
                    {
                        "type": presence_service.SCHEDULE_SOURCE,
                        "label": (
                            "Dars jadvali + davomat jurnali — "
                            f"{now.strftime('%d.%m.%Y')}"
                        ),
                    }
                ],
            )
        summary = presence_service.group_presence(db, user)
        return ToolResult(
            text=presence_service.format_group_presence_for_tool(summary),
            sources=[summary.source],
        )

    student = _find_student(db, asked)
    if student is None:
        return ToolResult(text=f"'{asked}' nomli talaba topilmadi.", ok=False)
    if not can_access_user(db, user, student):
        return ToolResult(
            text=(
                f"Ruxsat yo'q: {student.full_name} sizning doirangizga kirmaydi. "
                "Uning davomatini foydalanuvchiga bermang."
            ),
            ok=False,
        )
    return _student_summary(db, student, days)


register(
    Tool(
        name=NAME,
        description=(
            "Davomat svodini o'qiydi: oxirgi kunlardagi darslar soni, kelgan/"
            "kechikkan/kelmagan va foiz, fan kesimida taqsimot. Talabaga — o'z "
            "davomati, o'qituvchiga — bugungi darslarida davomat belgilangan-"
            "belgilanmagani, tyutor/dekanatga — doirasidagi talaba yoki butun "
            "guruh svodi. 'Davomatim qanday?', 'necha dars qoldirdim?', "
            "'guruhimda bugun kim kelmadi?' kabi savollarda ishlat."
        ),
        parameters={
            "type": "object",
            "properties": {
                "talaba": {
                    "type": "string",
                    "description": (
                        "Talabaning ismi yoki logini. Bo'sh bo'lsa: talaba "
                        "uchun — o'zi, o'qituvchi uchun — bugungi darslari, "
                        "tyutor/dekanat uchun — butun guruh svodi."
                    ),
                },
                "kunlar": {
                    "type": "integer",
                    "description": (
                        "Necha kunlik oraliq (default 7, maksimum 60)."
                    ),
                },
            },
            "required": [],
        },
        handler=handler,
        # Open to every role: the scope check is in the data layer.
        roles=ALL_ROLES,
    )
)
