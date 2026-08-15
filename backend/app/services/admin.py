"""Admin service (S13): user management, document upload, stats, demo reset.

Three jobs, one place:

1. **Users / roles** — the only place in the project that creates a `User`
   outside the seed. Passwords go through `auth/passwords.hash_password`.
2. **Document upload + tagging** — the file is stored under `uploads/documents/`
   (never in `seed/documents/`, so a demo reset cannot delete it), a `Document`
   row is written and the S3 pipeline indexes it immediately, so an uploaded
   document is searchable in the very next chat question.
3. **Stats + demo reset** — the numbers are *collected*, not re-queried: every
   figure comes from an existing service called with the admin user (whose
   scope is "everything"). The reset runs the same two steps the CLI does:
   `seed.generate.main()` and `rag.ingest.ingest_all(reset=True)`.

Access control is NOT re-implemented here: the router guards every endpoint
with `rbac.require_role()` (no arguments = admin only).
"""

from __future__ import annotations

import re
import sys
import threading
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.orchestrator import DISCLAIMER
from app.auth.passwords import hash_password
from app.config import get_settings
from app.models import (
    AccessLevel,
    Chunk,
    Document,
    DocumentType,
    Group,
    Notification,
    User,
    UserRole,
)
from app.rag import ingest as rag_ingest
from app.services import docflow, documents as documents_service
from app.services import notifications as notifications_service
from app.services import payments as payments_service
from app.services import presence as presence_service

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

SOURCE_TYPE = "admin"

MIN_PASSWORD_LENGTH = 6

# Upload accepts exactly what the RAG pipeline can read (one list, one place).
SUPPORTED_SUFFIXES = rag_ingest.SUPPORTED_SUFFIXES

ROLE_LABELS = {
    UserRole.student: "talaba",
    UserRole.teacher: "o'qituvchi",
    UserRole.tutor: "tyutor",
    UserRole.staff: "dekanat",
    UserRole.admin: "admin",
}

RESET_IDLE_MESSAGE = "Demo reset hali ishga tushirilmagan."
RESET_RUNNING_MESSAGE = "Demo ma'lumot qayta yaratilmoqda (seed + indekslash)…"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


# --- errors -----------------------------------------------------------------


class AdminError(RuntimeError):
    """Base class for admin management failures (routers map these to codes)."""


class DuplicateUsernameError(AdminError):
    """Username already taken."""


class WeakPasswordError(AdminError):
    """Password shorter than MIN_PASSWORD_LENGTH."""


class UnknownGroupError(AdminError):
    """group_id does not exist."""


class SelfDemotionError(AdminError):
    """An admin may not take the admin role away from themselves."""


class UnsupportedFileError(AdminError):
    """Only the text formats the RAG pipeline can read (.md/.txt)."""


class EmptyFileError(AdminError):
    """Uploaded file has no readable text."""


# --- data structures --------------------------------------------------------


@dataclass
class AdminUserRow:
    id: int
    username: str
    full_name: str
    role: UserRole
    role_label: str
    group_id: int | None
    group_name: str | None
    faculty_id: int | None
    language: str
    created_at: datetime


@dataclass
class AdminDocumentRow:
    id: int
    title: str
    doc_type: DocumentType
    language: str
    access_level: AccessLevel
    file_path: str | None
    uploaded_at: datetime
    chunk_count: int
    indexed: bool
    uploaded: bool  # admin upload (lives under uploads/) vs. seed corpus


@dataclass
class RoleCount:
    role: UserRole
    label: str
    count: int


@dataclass
class UserStats:
    total: int
    by_role: list[RoleCount]
    group_count: int
    faculty_count: int


@dataclass
class CorpusStats:
    document_count: int
    indexed_count: int
    chunk_count: int
    uploaded_count: int


@dataclass
class PaymentStats:
    student_count: int
    total_amount: float
    paid_amount: float
    pending_amount: float
    remaining_amount: float
    debtor_count: int
    partial_count: int
    paid_count: int
    pending_count: int


@dataclass
class PresenceStats:
    at: datetime
    current_pair: int | None
    pair_label: str | None
    student_count: int
    inside_count: int
    left_count: int
    absent_count: int
    attendance_percent: int | None


@dataclass
class TeacherStats:
    teacher_count: int
    inside_count: int
    absent_count: int
    class_count: int
    held_count: int
    at_risk_count: int
    unclear_count: int


@dataclass
class DocflowStats:
    total: int
    new_count: int
    open_count: int
    overdue_count: int
    due_soon_count: int


@dataclass
class NotificationStats:
    total: int
    unread_count: int


@dataclass
class AdminStats:
    generated_at: datetime
    users: UserStats
    corpus: CorpusStats
    payments: PaymentStats
    presence: PresenceStats
    teachers: TeacherStats
    docflow: DocflowStats
    notifications: NotificationStats
    source: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


@dataclass
class ResetState:
    """Progress of the demo reset (one at a time, module-level flag)."""

    running: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None
    ok: bool | None = None
    message: str = RESET_IDLE_MESSAGE
    documents: int = 0
    chunks: int = 0


# --- users ------------------------------------------------------------------


def role_label(role: UserRole) -> str:
    return ROLE_LABELS.get(role, role.value)


def _group_names(db: Session) -> dict[int, str]:
    return {gid: name for gid, name in db.query(Group.id, Group.name).all()}


def _row_of(user: User, names: dict[int, str]) -> AdminUserRow:
    return AdminUserRow(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        role_label=role_label(user.role),
        group_id=user.group_id,
        group_name=names.get(user.group_id or -1),
        faculty_id=user.faculty_id,
        language=user.language,
        created_at=user.created_at,
    )


def list_users(
    db: Session, role: UserRole | None = None, query: str | None = None
) -> list[AdminUserRow]:
    """Every account, newest last. Optional role filter and name/login search."""
    rows = db.query(User)
    if role is not None:
        rows = rows.filter(User.role == role)
    text = (query or "").strip()
    if text:
        pattern = f"%{text}%"
        rows = rows.filter(User.full_name.ilike(pattern) | User.username.ilike(pattern))
    names = _group_names(db)
    return [
        _row_of(user, names)
        for user in rows.order_by(User.role, User.full_name).all()
    ]


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def user_row(db: Session, user: User) -> AdminUserRow:
    return _row_of(user, _group_names(db))


def _check_group(db: Session, group_id: int | None) -> None:
    if group_id is not None and db.get(Group, group_id) is None:
        raise UnknownGroupError(group_id)


def create_user(
    db: Session,
    *,
    username: str,
    full_name: str,
    role: UserRole,
    password: str,
    group_id: int | None = None,
    faculty_id: int | None = None,
    language: str = "uz",
) -> User:
    """Create an account (synthetic data only — domain rule 1)."""
    login = (username or "").strip().lower()
    if not login:
        raise AdminError("Login bo'sh bo'lishi mumkin emas")
    if db.query(User.id).filter(User.username == login).first():
        raise DuplicateUsernameError(login)
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(MIN_PASSWORD_LENGTH)
    _check_group(db, group_id)

    user = User(
        username=login,
        full_name=(full_name or "").strip() or login,
        role=role,
        password_hash=hash_password(password),
        group_id=group_id,
        faculty_id=faculty_id,
        language=(language or "uz").strip() or "uz",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    actor: User,
    target: User,
    *,
    role: UserRole | None = None,
    full_name: str | None = None,
    group_id: int | None = None,
    faculty_id: int | None = None,
    language: str | None = None,
    password: str | None = None,
) -> User:
    """Change a role (the main use) and the other editable fields."""
    if role is not None and role != target.role:
        if target.id == actor.id:
            # Losing your own admin rights would lock the panel for everyone.
            raise SelfDemotionError(target.id)
        target.role = role
    if full_name is not None and full_name.strip():
        target.full_name = full_name.strip()
    if group_id is not None:
        _check_group(db, group_id or None)
        target.group_id = group_id or None
    if faculty_id is not None:
        target.faculty_id = faculty_id or None
    if language is not None and language.strip():
        target.language = language.strip()
    if password is not None and password != "":
        if len(password) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(MIN_PASSWORD_LENGTH)
        target.password_hash = hash_password(password)
    db.commit()
    db.refresh(target)
    return target


# --- documents --------------------------------------------------------------


def uploads_dir() -> Path:
    """`uploads/documents/` (relative paths resolve against backend/)."""
    raw = Path(get_settings().uploads_path)
    base = raw if raw.is_absolute() else (BACKEND_DIR / raw)
    return (base / "documents").resolve()


def safe_filename(name: str) -> str:
    """`Buyruq 91-M.md` -> `Buyruq_91-M.md` (path separators stripped)."""
    stem = Path(name or "").name
    cleaned = _SAFE_NAME_RE.sub("_", stem).strip("._-")
    return cleaned or "hujjat.md"


def _target_path(filename: str) -> Path:
    directory = uploads_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / safe_filename(filename)
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    counter = 2
    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def relative_path(path: Path) -> str:
    """Store `Document.file_path` relative to backend/ (S1 convention)."""
    try:
        return path.resolve().relative_to(BACKEND_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def is_uploaded(document: Document) -> bool:
    """True when the file lives in the upload folder (not the seed corpus)."""
    raw = Path(document.file_path or "")
    if not raw.parts:
        return False
    absolute = raw if raw.is_absolute() else (BACKEND_DIR / raw)
    try:
        absolute.resolve().relative_to(uploads_dir())
    except ValueError:
        return False
    return True


def chunk_counts(db: Session) -> dict[int, int]:
    rows = db.query(Chunk.document_id, func.count(Chunk.id)).group_by(
        Chunk.document_id
    )
    return {document_id: count for document_id, count in rows}


def list_documents(db: Session, user: User) -> list[AdminDocumentRow]:
    """Every document the caller may see + its indexing state."""
    counts = chunk_counts(db)
    rows = []
    for document in documents_service.visible_documents(db, user):
        count = counts.get(document.id, 0)
        rows.append(
            AdminDocumentRow(
                id=document.id,
                title=document.title,
                doc_type=document.doc_type,
                language=document.language,
                access_level=document.access_level,
                file_path=document.file_path,
                uploaded_at=document.uploaded_at,
                chunk_count=count,
                indexed=count > 0,
                uploaded=is_uploaded(document),
            )
        )
    return rows


def upload_document(
    db: Session,
    *,
    filename: str,
    content: bytes,
    title: str,
    doc_type: DocumentType,
    language: str = "uz",
    access_level: AccessLevel = AccessLevel.public,
    uploaded_by: int | None = None,
) -> tuple[Document, int]:
    """Save + register + index one uploaded file. Returns (document, chunks).

    Indexing happens right here (not in a background job): the DoD of S13 is
    that an uploaded document is findable in the very next search.

    Publishing also announces itself (S14, FUNKSIONALLIK 3.10 "Yangi buyruq
    e'lon qilindi"): everyone whose role may read the document gets one
    notification, the uploading admin excluded.
    """
    suffix = Path(safe_filename(filename)).suffix.lower()
    if suffix not in rag_ingest.SUPPORTED_SUFFIXES:
        raise UnsupportedFileError(suffix or filename)
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UnsupportedFileError("utf-8") from exc
    if not text.strip():
        raise EmptyFileError(filename)

    path = _target_path(filename)
    path.write_text(text, encoding="utf-8")

    document = Document(
        title=(title or "").strip() or Path(filename).stem,
        doc_type=doc_type,
        language=(language or "uz").strip() or "uz",
        access_level=access_level,
        file_path=relative_path(path),
    )
    db.add(document)
    db.flush()  # assigns document.id, needed by the Chroma ids

    chunks = rag_ingest.ingest_document(db, document)
    db.commit()
    db.refresh(document)
    notifications_service.notify_new_document(
        db, document, exclude_user_id=uploaded_by
    )
    return document, chunks


# --- stats ------------------------------------------------------------------


def stats_source(generated_at: datetime) -> dict:
    return {
        "type": SOURCE_TYPE,
        "label": (
            "Boshqaruv paneli statistikasi, "
            f"{generated_at.strftime('%d.%m.%Y %H:%M')}"
        ),
    }


def stats(db: Session, admin: User, now: datetime | None = None) -> AdminStats:
    """Every number on the admin dashboard, collected from existing services.

    The admin's scope is "everything", so calling the very same functions the
    tutor / dean pages use gives university-wide figures — no new SQL, and no
    second definition of "debtor" or "at risk" to drift apart.
    """
    moment = now or datetime.now()

    by_role = [
        RoleCount(
            role=role,
            label=role_label(role),
            count=db.query(User.id).filter(User.role == role).count(),
        )
        for role in UserRole
    ]
    users = UserStats(
        total=db.query(User.id).count(),
        by_role=by_role,
        group_count=db.query(Group.id).count(),
        faculty_count=len(
            {
                faculty_id
                for (faculty_id,) in db.query(Group.faculty_id).distinct().all()
                if faculty_id is not None
            }
        ),
    )

    document_rows = list_documents(db, admin)
    corpus = CorpusStats(
        document_count=len(document_rows),
        indexed_count=sum(1 for row in document_rows if row.indexed),
        chunk_count=sum(row.chunk_count for row in document_rows),
        uploaded_count=sum(1 for row in document_rows if row.uploaded),
    )

    money = payments_service.group_payment_summary(db, admin)
    payments = PaymentStats(
        student_count=len(money.rows),
        total_amount=money.total_amount,
        paid_amount=money.paid_amount,
        pending_amount=money.pending_amount,
        remaining_amount=money.remaining_amount,
        debtor_count=money.debtor_count,
        partial_count=money.partial_count,
        paid_count=money.paid_count,
        pending_count=money.pending_count,
    )

    group = presence_service.group_presence(db, admin, now=moment)
    presence = PresenceStats(
        at=group.at,
        current_pair=group.current_pair,
        pair_label=group.pair_label,
        student_count=len(group.rows),
        inside_count=group.inside_count,
        left_count=group.left_count,
        absent_count=group.absent_count,
        attendance_percent=group.attendance_percent,
    )

    # notify=False: opening the dashboard must not write teacher-absence
    # notifications (that stays the dean's own page, S10 decision).
    overview = presence_service.teacher_day_overview(
        db, admin, now=moment, notify=False
    )
    teachers = TeacherStats(
        teacher_count=overview.teacher_count,
        inside_count=overview.inside_count,
        absent_count=overview.absent_count,
        class_count=overview.class_count,
        held_count=overview.held_count,
        at_risk_count=overview.at_risk_count,
        unclear_count=overview.unclear_count,
    )

    flows = docflow.overview(db, admin)
    flow_stats = DocflowStats(
        total=flows.total,
        new_count=flows.new_count,
        open_count=flows.open_count,
        overdue_count=flows.overdue_count,
        due_soon_count=flows.due_soon_count,
    )

    # System-wide, not the admin's own bell: `notifications.feed()` answers
    # "my notifications" (the admin has none), while the panel reports how much
    # the whole system has produced.
    notifications = NotificationStats(
        total=db.query(Notification.id).count(),
        unread_count=db.query(Notification.id)
        .filter(Notification.is_read.is_(False))
        .count(),
    )

    return AdminStats(
        generated_at=moment,
        users=users,
        corpus=corpus,
        payments=payments,
        presence=presence,
        teachers=teachers,
        docflow=flow_stats,
        notifications=notifications,
        source=stats_source(moment),
    )


# --- demo reset -------------------------------------------------------------

_reset_lock = threading.Lock()
_reset_state = ResetState()


def reset_status() -> ResetState:
    """A copy of the current state (callers must not mutate the flag)."""
    with _reset_lock:
        return replace(_reset_state)


def begin_reset() -> bool:
    """Claim the reset slot. False when one is already running."""
    global _reset_state
    with _reset_lock:
        if _reset_state.running:
            return False
        _reset_state = ResetState(
            running=True,
            started_at=datetime.now(),
            message=RESET_RUNNING_MESSAGE,
        )
        return True


def finish_reset(
    ok: bool, message: str, documents: int = 0, chunks: int = 0
) -> ResetState:
    global _reset_state
    with _reset_lock:
        _reset_state = ResetState(
            running=False,
            started_at=_reset_state.started_at,
            finished_at=datetime.now(),
            ok=ok,
            message=message,
            documents=documents,
            chunks=chunks,
        )
        return replace(_reset_state)


def run_reset() -> ResetState:
    """The two steps the CLI does, in one call (~15-30 s, background task).

        python -m seed.generate --reset      (all tables)
        ingest_all(db, reset=True)           (Chroma + Chunk rows)

    Without the second step search would come back empty, so they always run
    together. The caller must have claimed the slot with `begin_reset()`.
    """
    from app.db import SessionLocal
    from seed import generate

    try:
        argv_backup = sys.argv
        sys.argv = ["seed.generate", "--reset"]
        try:
            code = generate.main()
        finally:
            sys.argv = argv_backup
        if code != 0:
            return finish_reset(False, "Demo ma'lumot generatori xato qaytardi")

        db = SessionLocal()
        try:
            report = rag_ingest.ingest_all(db, reset=True)
        finally:
            db.close()
        return finish_reset(
            True,
            (
                "Demo ma'lumot qayta yaratildi: "
                f"{report['documents']} hujjat, {report['chunks']} bo'lak "
                "indekslandi. Sessiyalar bekor qilindi — qaytadan kiring."
            ),
            documents=report["documents"],
            chunks=report["chunks"],
        )
    except Exception as exc:  # noqa: BLE001 - the panel must show the reason
        return finish_reset(False, f"Demo reset xatosi: {exc}")
