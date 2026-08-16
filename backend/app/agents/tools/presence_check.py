"""`mavjudlik_tekshir` — "is X in the university right now?"

The tool wrapper only decides **whose** presence is meant; the answer itself
comes from `services/presence.py`, the same code path the tutor's page and the
teacher's marking sheet use.

Permission has two layers (domain rule 2):
    1. the registry checks the role — this tool is open to everyone, because
       the real restriction is in the data layer,
    2. `can_access_user` decides *whose* presence may be read: a student only
       their own, a teacher/tutor their groups, staff their faculty, admin all.

Domain rule 6 lives in the service: the room is always reported as an
inference ("jadval bo'yicha"), the turnstile time as a fact.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.registry import ALL_ROLES, Tool, ToolResult, register
from app.auth.rbac import can_access_user
from app.models import User, UserRole
from app.services import presence as presence_service

NAME = "mavjudlik_tekshir"

SELF_WORDS = {"men", "o'zim", "ozim", "menda", "o'zimni"}


def _find_person(db: Session, name: str) -> User | None:
    cleaned = name.strip()
    if not cleaned:
        return None
    query = db.query(User)
    return (
        query.filter(User.username.ilike(cleaned)).first()
        or query.filter(User.full_name.ilike(f"%{cleaned}%")).first()
    )


def parse_moment(raw: str) -> datetime | None:
    """`vaqt`: "11:40" or a full ISO timestamp. Anything else -> now."""
    value = (raw or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    for fmt in ("%H:%M", "%H.%M"):
        try:
            clock = datetime.strptime(value, fmt).time()
        except ValueError:
            continue
        return datetime.combine(datetime.now().date(), clock)
    return None


def _answer(db: Session, person: User, moment: datetime | None) -> ToolResult:
    item = presence_service.presence(db, person, moment)
    return ToolResult(
        text=presence_service.format_presence_for_tool(item),
        sources=item.sources,
    )


def handler(db: Session, user: User, args: dict) -> ToolResult:
    asked = str(args.get("talaba") or args.get("shaxs") or "").strip()
    moment = parse_moment(str(args.get("vaqt") or ""))

    if not asked or asked.lower() in SELF_WORDS:
        return _answer(db, user, moment)

    if user.role == UserRole.student:
        # A student may ask about themselves only — by any name they like.
        if asked.lower() not in {user.username.lower(), user.full_name.lower()}:
            other = _find_person(db, asked)
            if other is None or other.id != user.id:
                return ToolResult(
                    text=(
                        f"Ruxsat yo'q: '{asked}' ning mavjudligi sizga ochiq emas. "
                        "Talaba faqat o'z holatini ko'ra oladi — foydalanuvchiga "
                        "shuni ayting."
                    ),
                    ok=False,
                )
        return _answer(db, user, moment)

    person = _find_person(db, asked)
    if person is None:
        return ToolResult(text=f"'{asked}' nomli foydalanuvchi topilmadi.", ok=False)
    if not can_access_user(db, user, person):
        return ToolResult(
            text=(
                f"Ruxsat yo'q: {person.full_name} sizning doirangizga kirmaydi. "
                "Uning joylashuvi va davomatini foydalanuvchiga bermang."
            ),
            ok=False,
        )
    return _answer(db, person=person, moment=moment)


register(
    Tool(
        name=NAME,
        description=(
            "Talaba yoki o'qituvchining hozirgi holatini aytadi: turniket logi "
            "bo'yicha binoda/binoda emas (kirgan-chiqqan vaqti bilan), jadval "
            "bo'yicha qaysi para va qaysi xonada bo'lishi kerakligi hamda "
            "davomatda belgilangan-belgilanmagani. 'Aliyev hozir "
            "universitetdami?', 'kim binoda?', 'qaysi xonada?' kabi savollarda "
            "ishlat. Xona — jadvalga asoslangan xulosa, javobda 'jadval "
            "bo'yicha' deb ayt."
        ),
        parameters={
            "type": "object",
            "properties": {
                "talaba": {
                    "type": "string",
                    "description": (
                        "Kimning holati: ism yoki login. Bo'sh bo'lsa — "
                        "so'ragan foydalanuvchining o'zi."
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
        # Open to every role on purpose: the restriction is in the data layer
        # (`can_access_user`), so a tutor sees their groups and a student only
        # themselves — while everyone can ask "am I marked in class?".
        roles=ALL_ROLES,
    )
)
