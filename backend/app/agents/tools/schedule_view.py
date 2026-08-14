"""`jadval_kor` — class schedule, always inside the caller's RBAC scope.

Scope (auth/rbac.py helpers, never a hand-rolled role check):
    student -> own group          teacher -> own classes
    tutor   -> own groups         staff   -> own faculty's groups
    admin   -> everything
A group outside that scope is refused with a tool result, not silently ignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.agents.registry import ALL_ROLES, Tool, ToolResult, register
from app.auth.rbac import visible_group_ids
from app.models import Group, Schedule, User, UserRole

# Pair times live in ONE place (S9): services/presence.py — the same table the
# seed, the presence service and the internal regulations (3.1) use.
from app.services.presence import PAIR_TIME_LABELS as PAIR_TIMES

NAME = "jadval_kor"

WEEKDAYS = [
    "Dushanba",
    "Seshanba",
    "Chorshanba",
    "Payshanba",
    "Juma",
    "Shanba",
    "Yakshanba",
]
_WEEKDAY_ALIASES = {name.lower(): i for i, name in enumerate(WEEKDAYS)}
_WEEK_WORDS = {"hafta", "haftalik", "butun hafta", "hammasi", "barcha"}
MAX_ROWS = 60


@dataclass
class _Day:
    weekday: int
    on_date: date | None
    label: str


def _day_label(weekday: int, on_date: date | None, suffix: str = "") -> str:
    label = WEEKDAYS[weekday]
    if on_date is not None:
        label = f"{label} ({on_date.isoformat()}{', ' + suffix if suffix else ''})"
    elif suffix:
        label = f"{label} ({suffix})"
    return label


def _resolve_days(raw: str) -> tuple[list[_Day], str | None]:
    """Parse the `kun` argument. Returns (days, error_text)."""
    today = date.today()
    value = (raw or "").strip().lower()

    if not value or value in {"bugun", "hozir", "bugungi"}:
        return [_Day(today.weekday(), today, _day_label(today.weekday(), today, "bugun"))], None
    if value in {"ertaga", "ertangi"}:
        d = today + timedelta(days=1)
        return [_Day(d.weekday(), d, _day_label(d.weekday(), d, "ertaga"))], None
    if value in {"kecha", "kechagi"}:
        d = today - timedelta(days=1)
        return [_Day(d.weekday(), d, _day_label(d.weekday(), d, "kecha"))], None
    if value in _WEEK_WORDS:
        # Mon-Sat: Sunday is free in the seed schedule
        return [_Day(wd, None, WEEKDAYS[wd]) for wd in range(6)], None
    if value in _WEEKDAY_ALIASES:
        wd = _WEEKDAY_ALIASES[value]
        return [_Day(wd, None, WEEKDAYS[wd])], None
    try:
        d = date.fromisoformat(value)
    except ValueError:
        return [], (
            f"'{raw}' kunini tushunmadim. Ruxsat etilgan qiymatlar: bugun, ertaga, "
            "kecha, hafta, hafta kuni nomi (dushanba…shanba) yoki YYYY-MM-DD sana."
        )
    return [_Day(d.weekday(), d, _day_label(d.weekday(), d))], None


def _resolve_group(db: Session, name: str) -> Group | None:
    cleaned = name.strip()
    exact = db.query(Group).filter(Group.name.ilike(cleaned)).first()
    return exact or db.query(Group).filter(Group.name.ilike(f"%{cleaned}%")).first()


def _resolve_teacher(db: Session, name: str) -> User | None:
    cleaned = name.strip()
    query = db.query(User).filter(User.role == UserRole.teacher)
    return (
        query.filter(User.username.ilike(cleaned)).first()
        or query.filter(User.full_name.ilike(f"%{cleaned}%")).first()
    )


def handler(db: Session, user: User, args: dict) -> ToolResult:
    days, error = _resolve_days(str(args.get("kun") or ""))
    if error:
        return ToolResult(text=error, ok=False)

    visible = visible_group_ids(db, user)  # None = admin, no restriction
    if visible is not None and not visible:
        return ToolResult(text="Sizga biriktirilgan guruh topilmadi — jadval bo'sh.")

    query = db.query(Schedule)
    scope_note = ""

    if visible is not None:
        query = query.filter(Schedule.group_id.in_(visible))
    if user.role == UserRole.teacher:
        query = query.filter(Schedule.teacher_id == user.id)
        scope_note = "o'z darslaringiz"

    group_name = str(args.get("guruh") or "").strip()
    if group_name:
        group = _resolve_group(db, group_name)
        if group is None:
            return ToolResult(text=f"'{group_name}' nomli guruh topilmadi.", ok=False)
        if visible is not None and group.id not in visible:
            return ToolResult(
                text=(
                    f"Ruxsat yo'q: '{group.name}' guruhi sizning doirangizga kirmaydi. "
                    "Foydalanuvchiga bu guruh jadvalini ko'rsatolmasligingizni ayting."
                ),
                ok=False,
            )
        query = query.filter(Schedule.group_id == group.id)
        scope_note = group.name

    teacher_name = str(args.get("oqituvchi") or "").strip()
    if teacher_name:
        teacher = _resolve_teacher(db, teacher_name)
        if teacher is None:
            return ToolResult(
                text=f"'{teacher_name}' nomli o'qituvchi topilmadi.", ok=False
            )
        query = query.filter(Schedule.teacher_id == teacher.id)
        scope_note = f"{scope_note}, {teacher.full_name}" if scope_note else teacher.full_name

    weekdays = sorted({d.weekday for d in days})
    rows = (
        query.filter(Schedule.weekday.in_(weekdays))
        .order_by(Schedule.weekday, Schedule.pair_number, Schedule.group_id)
        .limit(MAX_ROWS)
        .all()
    )
    if not rows:
        where = f" ({scope_note})" if scope_note else ""
        listed = ", ".join(d.label for d in days)
        return ToolResult(text=f"{listed} uchun jadvalda dars topilmadi{where}.")

    names = _lookup_names(db, rows)
    lines, sources = [], []
    for day in days:
        day_rows = [r for r in rows if r.weekday == day.weekday]
        if not day_rows:
            continue
        lines.append(f"{day.label}:")
        for row in day_rows:
            start, end = PAIR_TIMES.get(row.pair_number, ("?", "?"))
            lines.append(
                f"  {row.pair_number}-juftlik {start}-{end} — {row.subject}, "
                f"{row.room}-xona, {names['groups'].get(row.group_id, '?')}, "
                f"o'qituvchi: {names['teachers'].get(row.teacher_id, '?')}"
            )
        sources.append(
            {
                "type": "schedule",
                "label": f"Dars jadvali — {day.label}"
                + (f", {scope_note}" if scope_note else ""),
            }
        )

    lines.append(
        "(Ma'lumot dars jadvaliga asoslangan — amaldagi o'zgarishlar bo'lishi mumkin.)"
    )
    return ToolResult(text="\n".join(lines), sources=sources)


def _lookup_names(db: Session, rows: list[Schedule]) -> dict[str, dict[int, str]]:
    group_ids = {r.group_id for r in rows}
    teacher_ids = {r.teacher_id for r in rows}
    groups = db.query(Group.id, Group.name).filter(Group.id.in_(group_ids)).all()
    teachers = db.query(User.id, User.full_name).filter(User.id.in_(teacher_ids)).all()
    return {
        "groups": {gid: name for gid, name in groups},
        "teachers": {tid: name for tid, name in teachers},
    }


register(
    Tool(
        name=NAME,
        description=(
            "Dars jadvalini o'qiydi. Talabaga — o'z guruhi, o'qituvchiga — o'z "
            "darslari, tyutorga — o'z guruhlari, dekanat/adminga — so'ralgan "
            "guruh yoki o'qituvchi jadvali. 'Bugun qanday darslar bor?', "
            "'qaysi xonada?', 'nechanchi juftlik?' kabi savollarda ishlat."
        ),
        parameters={
            "type": "object",
            "properties": {
                "kun": {
                    "type": "string",
                    "description": (
                        "Qaysi kun: 'bugun' (default), 'ertaga', 'kecha', 'hafta' "
                        "(butun hafta), hafta kuni nomi ('dushanba'…'shanba') yoki "
                        "YYYY-MM-DD sana."
                    ),
                },
                "guruh": {
                    "type": "string",
                    "description": "Guruh nomi, masalan 'AT-24-01'. Bo'sh bo'lsa — o'z doirangiz.",
                },
                "oqituvchi": {
                    "type": "string",
                    "description": "O'qituvchi ismi yoki logini (dekanat/admin uchun).",
                },
            },
            "required": [],
        },
        handler=handler,
        roles=ALL_ROLES,
    )
)
