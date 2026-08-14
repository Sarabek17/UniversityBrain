"""Presence + attendance endpoints. Thin layer: logic lives in services/presence.py.

    GET  /attendance/presence[?at=]            -> own presence
    GET  /attendance/presence/{user_id}[?at=]  -> someone else's (scope: 403)
    GET  /attendance/group[?group_id=&at=]     -> group presence list (tutor/staff)
    GET  /attendance/summary[?student_id=&days=] -> attendance history
    GET  /attendance/my-classes[?on_date=]     -> the teacher's classes for a day
    GET  /attendance/class/{schedule_id}       -> marking sheet (roster)
    POST /attendance/class/{schedule_id}/mark  -> write attendance + hold session
    GET  /attendance/teachers[?on_date=&at=]   -> today's teacher roll-call (staff)
    GET  /attendance/teachers/monthly[?days=]  -> held-class percentages (staff)

Two permission layers, as everywhere in this project: `require_role` decides
*who may call*, and the scope helpers of `auth/rbac.py` decide *about whom*.
Marking is narrower still — the teacher of that very class only (409/403 come
from the service, never from a hand-rolled role check here).

`at` / `on_date` are read-only "what if" parameters: the seed writes the whole
day in advance, so the demo can be shown at any hour (`?at=2026-08-14T11:40`).
"""

from dataclasses import asdict
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.rbac import ensure_can_access_user, get_current_user, require_role
from app.db import get_db
from app.models import User, UserRole
from app.schemas import (
    AttendanceMarkRequest,
    AttendanceSummaryOut,
    ClassRosterOut,
    GroupPresenceOut,
    PresenceOut,
    TeacherDayOut,
    TeacherDayOverviewOut,
    TeacherMonthOut,
)
from app.services import presence as presence_service

router = APIRouter(prefix="/attendance", tags=["attendance"])

_NO_USER = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi"
)
_NO_CLASS = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Dars jadvalida topilmadi"
)
_NOT_YOUR_CLASS = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Davomatni faqat shu darsning o'qituvchisi belgilay oladi",
)


def _user_or_404(db: Session, user_id: int) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise _NO_USER
    return target


def _schedule_or_404(db: Session, schedule_id: int):
    schedule = presence_service.get_schedule(db, schedule_id)
    if schedule is None:
        raise _NO_CLASS
    return schedule


@router.get("/presence", response_model=PresenceOut)
def own_presence(
    at: datetime | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenceOut:
    """Where the turnstile last saw me, and where the schedule says I should be."""
    return PresenceOut.model_validate(
        asdict(presence_service.presence(db, user, at))
    )


@router.get("/presence/{user_id}", response_model=PresenceOut)
def user_presence(
    user_id: int,
    at: datetime | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenceOut:
    """One person's presence. Outside the caller's scope -> 403."""
    target = _user_or_404(db, user_id)
    return PresenceOut.model_validate(
        asdict(presence_service.student_presence(db, user, target, at))
    )


@router.get("/group", response_model=GroupPresenceOut)
def group_presence(
    group_id: int | None = None,
    at: datetime | None = None,
    user: User = Depends(require_role(UserRole.tutor, UserRole.staff)),
    db: Session = Depends(get_db),
) -> GroupPresenceOut:
    """The tutor's list: inside / in class (confirmed) / left / never came."""
    try:
        summary = presence_service.group_presence(db, user, group_id, at)
    except presence_service.OutOfScopeError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu guruh sizning doirangizga kirmaydi",
        ) from None
    return GroupPresenceOut.model_validate(asdict(summary))


@router.get("/summary", response_model=AttendanceSummaryOut)
def attendance_summary(
    student_id: int | None = None,
    days: int = presence_service.DEFAULT_SUMMARY_DAYS,
    at: datetime | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttendanceSummaryOut:
    """Attendance history: own by default, another student inside scope (403)."""
    if student_id is None or student_id == user.id:
        summary = presence_service.attendance_summary(db, user, days, at)
    else:
        target = _user_or_404(db, student_id)
        summary = presence_service.student_attendance_summary(
            db, user, target, days, at
        )
    return AttendanceSummaryOut.model_validate(asdict(summary))


@router.get("/my-classes", response_model=TeacherDayOut)
def my_classes(
    on_date: date | None = None,
    at: datetime | None = None,
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
) -> TeacherDayOut:
    """The teacher's day: every class + how much of it is already marked."""
    moment = at or datetime.now()
    classes = presence_service.teacher_classes(db, user, on_date, moment)
    return TeacherDayOut(
        date=on_date or moment.date(),
        teacher_id=user.id,
        teacher_name=user.full_name,
        current_pair=presence_service.current_pair(moment),
        classes=[c.__dict__ for c in classes],
    )


@router.get("/teachers", response_model=TeacherDayOverviewOut)
def teacher_overview(
    on_date: date | None = None,
    at: datetime | None = None,
    user: User = Depends(require_role(UserRole.staff)),
    db: Session = Depends(get_db),
) -> TeacherDayOverviewOut:
    """Dean's roll-call: every teacher of the faculty + the state of their classes.

    A class that is at risk right now also writes a `Notification` for the
    faculty's dean's office (never a duplicate) — S12 renders those.
    Teachers and tutors get 403: this view is the dean's oversight tool
    (FUNKSIONALLIK 3.8 "maxfiylik").
    """
    overview = presence_service.teacher_day_overview(db, user, on_date, at)
    return TeacherDayOverviewOut.model_validate(asdict(overview))


@router.get("/teachers/monthly", response_model=TeacherMonthOut)
def teacher_monthly(
    days: int = presence_service.DEFAULT_MONTH_DAYS,
    at: datetime | None = None,
    user: User = Depends(require_role(UserRole.staff)),
    db: Session = Depends(get_db),
) -> TeacherMonthOut:
    """Report view: held / cancelled / unclear classes per teacher, in percent."""
    summary = presence_service.teacher_month_summary(db, user, days, at)
    return TeacherMonthOut.model_validate(asdict(summary))


@router.get("/class/{schedule_id}", response_model=ClassRosterOut)
def class_roster(
    schedule_id: int,
    on_date: date | None = None,
    at: datetime | None = None,
    user: User = Depends(
        require_role(UserRole.teacher, UserRole.tutor, UserRole.staff)
    ),
    db: Session = Depends(get_db),
) -> ClassRosterOut:
    """The marking sheet: journal state + turnstile hint for every student."""
    schedule = _schedule_or_404(db, schedule_id)
    if not presence_service.can_view_class(db, user, schedule):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu dars sizning doirangizga kirmaydi",
        )
    roster = presence_service.class_roster(db, user, schedule, on_date, at)
    return ClassRosterOut.model_validate(asdict(roster))


@router.post("/class/{schedule_id}/mark", response_model=ClassRosterOut)
def mark_class(
    schedule_id: int,
    payload: AttendanceMarkRequest,
    at: datetime | None = None,
    user: User = Depends(require_role(UserRole.teacher)),
    db: Session = Depends(get_db),
) -> ClassRosterOut:
    """One click: attendance rows written/updated, the session becomes `held`.

    Answers with the refreshed roster, so the page needs no second request.
    """
    schedule = _schedule_or_404(db, schedule_id)
    marks = {mark.student_id: mark.status for mark in payload.marks}
    if not marks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Belgilanadigan talaba ro'yxati bo'sh",
        )
    try:
        roster = presence_service.mark_attendance(
            db, user, schedule, marks, payload.on_date, at
        )
    except presence_service.NotOwnClassError:
        raise _NOT_YOUR_CLASS from None
    except presence_service.UnknownStudentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Bu talabalar guruhga kirmaydi: {exc}",
        ) from None
    return ClassRosterOut.model_validate(asdict(roster))
