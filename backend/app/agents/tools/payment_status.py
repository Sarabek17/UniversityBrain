"""`tolov_holati` — contract / payment state, always inside the caller's scope.

This file is only the *tool wrapper*: it decides **whose** contract is meant and
turns the answer into a `ToolResult`. The numbers themselves come from
`services/payments.py`, the exact same code path the "Kontrakt" page and the
tutor dashboard use.

Two layers of permission, as the domain rules demand:
    1. the registry refuses the tool outright for roles that may not see money
       (teacher — the handler is never called),
    2. inside the handler the scope helper decides *which* student:
       student -> only themselves, tutor -> their groups, staff -> their
       faculty, admin -> everyone (`can_access_user`).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.registry import Tool, ToolResult, register
from app.auth.rbac import can_access_user
from app.models import User, UserRole
from app.services import payments as payments_service

NAME = "tolov_holati"


def _find_student(db: Session, name: str) -> User | None:
    cleaned = name.strip()
    if not cleaned:
        return None
    query = db.query(User).filter(User.role == UserRole.student)
    return (
        query.filter(User.username.ilike(cleaned)).first()
        or query.filter(User.full_name.ilike(f"%{cleaned}%")).first()
    )


def _own_contract(db: Session, user: User) -> ToolResult:
    try:
        summary = payments_service.contract_summary(db, user)
    except payments_service.NoContractError:
        return ToolResult(
            text=f"{user.full_name} uchun kontrakt yozuvi topilmadi.", ok=False
        )
    return ToolResult(
        text=payments_service.format_contract_for_tool(summary),
        sources=[summary.source],
    )


def handler(db: Session, user: User, args: dict) -> ToolResult:
    asked = str(args.get("talaba") or "").strip()

    if user.role == UserRole.student:
        # A student may ask about themselves only — by any name they like.
        if asked and asked.lower() not in {
            user.username.lower(),
            user.full_name.lower(),
            "men",
            "o'zim",
            "ozim",
        }:
            other = _find_student(db, asked)
            if other is None or other.id != user.id:
                return ToolResult(
                    text=(
                        f"Ruxsat yo'q: '{asked}' ning to'lov ma'lumoti sizga ochiq "
                        "emas. Talaba faqat o'z kontraktini ko'ra oladi — "
                        "foydalanuvchiga shuni ayting."
                    ),
                    ok=False,
                )
        return _own_contract(db, user)

    if not asked:
        # tutor / staff / admin without a name: the whole scope at once
        # ("guruhimda kimlar qarzdor?").
        summary = payments_service.group_payment_summary(db, user)
        return ToolResult(
            text=payments_service.format_group_for_tool(summary),
            sources=[summary.source],
        )

    student = _find_student(db, asked)
    if student is None:
        return ToolResult(text=f"'{asked}' nomli talaba topilmadi.", ok=False)
    if not can_access_user(db, user, student):
        return ToolResult(
            text=(
                f"Ruxsat yo'q: {student.full_name} sizning doirangizga kirmaydi. "
                "Uning to'lov ma'lumotini foydalanuvchiga bermang."
            ),
            ok=False,
        )
    try:
        summary = payments_service.contract_summary(db, student)
    except payments_service.NoContractError:
        return ToolResult(
            text=f"{student.full_name} uchun kontrakt yozuvi topilmadi.", ok=False
        )
    return ToolResult(
        text=payments_service.format_contract_for_tool(summary),
        sources=[summary.source],
    )


register(
    Tool(
        name=NAME,
        description=(
            "Kontrakt to'lovi holatini o'qiydi: jami summa, to'langan, qoldiq, "
            "oxirgi to'lov va chek raqami. Talabaga — o'z kontrakti, "
            "tyutor/dekanatga — o'z doirasidagi talaba yoki butun guruh svodi "
            "(qarzdorlar ro'yxati). 'Kontraktimdan qancha qoldi?', 'chek "
            "tushdimi?', 'guruhimda kimlar qarzdor?' kabi savollarda ishlat."
        ),
        parameters={
            "type": "object",
            "properties": {
                "talaba": {
                    "type": "string",
                    "description": (
                        "Talabaning ismi yoki logini. Bo'sh bo'lsa: talaba uchun "
                        "— o'zi, tyutor/dekanat uchun — butun guruh svodi."
                    ),
                },
            },
            "required": [],
        },
        handler=handler,
        # teacher is intentionally absent: contract money is not their business
        # (FUNKSIONALLIK 3.6 "maxfiylik"). admin is always allowed by the registry.
        roles=(UserRole.student, UserRole.tutor, UserRole.staff),
    )
)
