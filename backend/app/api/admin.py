"""Admin endpoints. Thin layer: all logic lives in services/admin.py.

    GET    /admin/users[?role=&q=]  -> every account (role filter + search)
    POST   /admin/users             -> create an account (201)
    PATCH  /admin/users/{id}        -> change role / name / group / password
    GET    /admin/groups            -> group picker for the user form
    GET    /admin/documents         -> documents + their indexing state
    POST   /admin/documents         -> upload + tag + index a file (multipart)
    GET    /admin/stats             -> dashboard figures
    POST   /admin/reset             -> start the demo reset (202, background)
    GET    /admin/reset/status      -> progress of the running/last reset

RBAC: `require_role()` with **no arguments** — the allowed set is then just
`{admin}` (every other role gets 403 from the single mechanism in auth/rbac.py).
The dependency also hands back the admin `User`, which is what the stats
service needs: an admin's scope is "everything", so the existing tutor/dean
services return university-wide numbers unchanged.

The reset runs as a `BackgroundTask` because it takes ~15-30 s (the embedding
model is loaded and the whole corpus is re-indexed); the client polls
`/admin/reset/status` and logs out when it finishes — user ids are re-created,
so every token issued before the reset points at somebody else now.
"""

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.db import get_db
from app.models import AccessLevel, DocumentType, Group, User, UserRole
from app.schemas import (
    AdminDocumentOut,
    AdminGroupOut,
    AdminResetOut,
    AdminStatsOut,
    AdminUploadOut,
    AdminUserCreateIn,
    AdminUserOut,
    AdminUserUpdateIn,
)
from app.services import admin as admin_service

router = APIRouter(prefix="/admin", tags=["admin"])

_USER_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi"
)


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


# --- users ------------------------------------------------------------------


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    role: UserRole | None = None,
    q: str | None = None,
    user: User = Depends(require_role()),
    db: Session = Depends(get_db),
) -> list[AdminUserOut]:
    return [
        AdminUserOut.model_validate(row)
        for row in admin_service.list_users(db, role=role, query=q)
    ]


@router.post(
    "/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED
)
def create_user(
    payload: AdminUserCreateIn,
    user: User = Depends(require_role()),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    """Create an account. Duplicate login -> 409, weak password/group -> 422."""
    try:
        created = admin_service.create_user(
            db,
            username=payload.username,
            full_name=payload.full_name,
            role=payload.role,
            password=payload.password,
            group_id=payload.group_id,
            faculty_id=payload.faculty_id,
            language=payload.language,
        )
    except admin_service.DuplicateUsernameError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu login band — boshqa login tanlang",
        ) from None
    except admin_service.WeakPasswordError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Parol juda qisqa: kamida "
                f"{admin_service.MIN_PASSWORD_LENGTH} belgi"
            ),
        ) from None
    except admin_service.UnknownGroupError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bunday guruh yo'q",
        ) from None
    except admin_service.AdminError as exc:
        raise _bad_request(str(exc)) from None
    return AdminUserOut.model_validate(admin_service.user_row(db, created))


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    payload: AdminUserUpdateIn,
    user: User = Depends(require_role()),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    """Change a role (the main use). Unknown user -> 404, own demotion -> 409."""
    target = admin_service.get_user(db, user_id)
    if target is None:
        raise _USER_NOT_FOUND
    try:
        updated = admin_service.update_user(
            db,
            user,
            target,
            role=payload.role,
            full_name=payload.full_name,
            group_id=payload.group_id,
            faculty_id=payload.faculty_id,
            language=payload.language,
            password=payload.password,
        )
    except admin_service.SelfDemotionError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O'z rolingizni o'zgartira olmaysiz",
        ) from None
    except admin_service.WeakPasswordError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Parol juda qisqa: kamida "
                f"{admin_service.MIN_PASSWORD_LENGTH} belgi"
            ),
        ) from None
    except admin_service.UnknownGroupError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Bunday guruh yo'q",
        ) from None
    return AdminUserOut.model_validate(admin_service.user_row(db, updated))


@router.get("/groups", response_model=list[AdminGroupOut])
def list_groups(
    user: User = Depends(require_role()),
    db: Session = Depends(get_db),
) -> list[AdminGroupOut]:
    return db.query(Group).order_by(Group.id).all()


# --- documents --------------------------------------------------------------


@router.get("/documents", response_model=list[AdminDocumentOut])
def list_documents(
    user: User = Depends(require_role()),
    db: Session = Depends(get_db),
) -> list[AdminDocumentOut]:
    """Like `GET /documents`, plus the indexing state the admin has to see."""
    return [
        AdminDocumentOut.model_validate(row)
        for row in admin_service.list_documents(db, user)
    ]


@router.post(
    "/documents", response_model=AdminUploadOut, status_code=status.HTTP_201_CREATED
)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: DocumentType = Form(DocumentType.other),
    language: str = Form("uz"),
    access_level: AccessLevel = Form(AccessLevel.public),
    user: User = Depends(require_role()),
    db: Session = Depends(get_db),
) -> AdminUploadOut:
    """Upload + tag + index one document (`.md`/`.txt`).

    Indexing is part of the request: when this returns, the document is already
    findable by `hujjat_qidir` (the S13 DoD).
    """
    content = file.file.read()
    try:
        document, chunks = admin_service.upload_document(
            db,
            filename=file.filename or title,
            content=content,
            title=title,
            doc_type=doc_type,
            language=language,
            access_level=access_level,
            uploaded_by=user.id,
        )
    except admin_service.UnsupportedFileError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Faqat matnli fayllar qo'llab-quvvatlanadi: "
                + ", ".join(sorted(admin_service.SUPPORTED_SUFFIXES))
            ),
        ) from None
    except admin_service.EmptyFileError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Fayl matni bo'sh",
        ) from None
    finally:
        file.file.close()

    rows = {row.id: row for row in admin_service.list_documents(db, user)}
    return AdminUploadOut(
        document=AdminDocumentOut.model_validate(rows[document.id]),
        chunks=chunks,
        message=f"«{document.title}» yuklandi va {chunks} bo'lakda indekslandi",
    )


# --- stats + demo reset -----------------------------------------------------


@router.get("/stats", response_model=AdminStatsOut)
def get_stats(
    user: User = Depends(require_role()),
    db: Session = Depends(get_db),
) -> AdminStatsOut:
    return AdminStatsOut.model_validate(admin_service.stats(db, user))


@router.get("/reset/status", response_model=AdminResetOut)
def reset_status(user: User = Depends(require_role())) -> AdminResetOut:
    return AdminResetOut.model_validate(admin_service.reset_status())


@router.post(
    "/reset", response_model=AdminResetOut, status_code=status.HTTP_202_ACCEPTED
)
def reset_demo(
    background: BackgroundTasks,
    user: User = Depends(require_role()),
) -> AdminResetOut:
    """Start the demo reset. A second request while one runs -> 409."""
    if not admin_service.begin_reset():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Demo reset allaqachon ishlamoqda",
        )
    background.add_task(admin_service.run_reset)
    return AdminResetOut.model_validate(admin_service.reset_status())
