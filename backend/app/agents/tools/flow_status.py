"""`ariza_holati` — "arizam qayerda?" (the demo question of FUNKSIONALLIK 3.9).

The wrapper only decides *which* document was asked about; the answer comes
from `services/docflow.py`, the very code path the `/docflow` page renders.

Permission has two layers (domain rule 2), the `mavjudlik_tekshir` pattern:
    1. the registry lets every role call the tool — the real restriction is in
       the data layer, not in the tool list,
    2. `services/docflow.can_view` decides *which* documents exist for the
       caller: the sender sees their own, the recipient sees theirs, a
       role-addressed document stays inside the sender's faculty. A stranger's
       application answers exactly like a missing one — its existence is never
       disclosed.

The answer always carries the mandatory citation (domain rule 5):
"Ariza №5, 12.08.2026, holat: tasdiqlandi" + the last history comment.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.registry import ALL_ROLES, Tool, ToolResult, register
from app.models import User
from app.services import docflow as docflow_service

NAME = "ariza_holati"

INBOX_WORDS = {"kelgan", "inbox", "kelganlar", "kirim"}
OUTBOX_WORDS = {"yuborilgan", "outbox", "mening", "arizalarim", "chiqim"}


def handler(db: Session, user: User, args: dict) -> ToolResult:
    asked = str(args.get("ariza") or args.get("hujjat") or "").strip()
    raw_box = str(args.get("yonalish") or "").strip().lower()
    box = (
        docflow_service.BOX_INBOX
        if raw_box in INBOX_WORDS
        else docflow_service.BOX_OUTBOX
        if raw_box in OUTBOX_WORDS
        else ""
    )

    if asked:
        flow = docflow_service.find_flow(db, user, asked)
        if flow is None:
            return ToolResult(
                text=(
                    f"'{asked}' bo'yicha sizga tegishli hujjat topilmadi. "
                    "Foydalanuvchiga boshqa birovning arizasi haqida ma'lumot "
                    "bermang."
                ),
                ok=False,
            )
        detail = docflow_service.flow_detail(db, user, flow)
        return ToolResult(
            text=docflow_service.format_flow_for_tool(detail),
            sources=[detail.source],
        )

    listing = docflow_service.overview(db, user, box)
    return ToolResult(
        text=docflow_service.format_flow_list_for_tool(listing),
        sources=[listing.source],
    )


register(
    Tool(
        name=NAME,
        description=(
            "Hujjat aylanmasidagi ariza/hisobot/buyruq holatini aytadi: "
            "yuborildi, ko'rildi, ijroda, tasdiqlandi yoki rad etildi — tarixi "
            "va oxirgi izohi bilan. 'Arizam qayerda?', 'ma'lumotnoma arizam "
            "tasdiqlandimi?', 'menga qanday hujjatlar keldi?', 'ijro muddati "
            "yaqin hujjatlar qaysi?' kabi savollarda ishlat. Javobda ariza "
            "raqami, sanasi va holatini manba sifatida keltir."
        ),
        parameters={
            "type": "object",
            "properties": {
                "ariza": {
                    "type": "string",
                    "description": (
                        "Aniq hujjat: raqami (masalan '5') yoki mavzusidagi "
                        "so'z ('ma'lumotnoma', 'hisobot'). Bo'sh bo'lsa — "
                        "barcha tegishli hujjatlar svodi."
                    ),
                },
                "yonalish": {
                    "type": "string",
                    "description": (
                        "'kelgan' — menga kelgan hujjatlar, 'yuborilgan' — "
                        "men yuborganlarim. Bo'sh bo'lsa: talaba/o'qituvchiga "
                        "— yuborilganlar, dekanat/tyutorga — kelganlar."
                    ),
                },
            },
            "required": [],
        },
        handler=handler,
        # Open to every role on purpose: the restriction is in the data layer
        # (`docflow.can_view`), so a student only ever sees their own
        # applications while the dean sees the faculty's inbox.
        roles=ALL_ROLES,
    )
)
