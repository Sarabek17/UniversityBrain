"""THE single RBAC mechanism for the whole project.

Every later session uses these dependencies/helpers — roles are never checked
manually anywhere else.

Usage in routers:

    from app.auth.rbac import get_current_user, require_role

    @router.get("/only-staff", dependencies=[Depends(require_role(UserRole.staff))])
    def staff_view(user: User = Depends(get_current_user)): ...

Scope helpers (data visibility, FUNKSIONALLIK "doira" rules):
    - student -> only their own data (own group for group-level views)
    - teacher -> groups they teach (via Schedule)
    - tutor   -> their groups (Group.tutor_id)
    - staff   -> their faculty (faculty_id)
    - admin   -> everything (no restriction)
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Group, Schedule, User, UserRole

_bearer = HTTPBearer(auto_error=False)

_CREDENTIALS_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Avtorizatsiya talab qilinadi",
    headers={"WWW-Authenticate": "Bearer"},
)


def create_access_token(user: User) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: decode the Bearer JWT and load the user. 401 otherwise."""
    if credentials is None:
        raise _CREDENTIALS_401
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.InvalidTokenError:
        raise _CREDENTIALS_401
    user = db.get(User, int(payload.get("sub", 0)))
    if user is None:
        raise _CREDENTIALS_401
    return user


def require_role(*roles: UserRole):
    """Dependency factory: allow only the listed roles (admin always allowed).

    Example: Depends(require_role(UserRole.staff)) -> staff or admin, else 403.
    """
    allowed = set(roles) | {UserRole.admin}

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu amal uchun ruxsatingiz yo'q",
            )
        return user

    return checker


# --- scope (doira) filter helpers -------------------------------------------


def visible_group_ids(db: Session, user: User) -> set[int] | None:
    """Group ids the user may see. None = unrestricted (admin)."""
    if user.role == UserRole.admin:
        return None
    if user.role == UserRole.tutor:
        rows = db.query(Group.id).filter(Group.tutor_id == user.id).all()
    elif user.role == UserRole.staff:
        rows = db.query(Group.id).filter(Group.faculty_id == user.faculty_id).all()
    elif user.role == UserRole.teacher:
        rows = (
            db.query(Schedule.group_id)
            .filter(Schedule.teacher_id == user.id)
            .distinct()
            .all()
        )
    else:  # student
        return {user.group_id} if user.group_id is not None else set()
    return {row[0] for row in rows}


def can_access_user(db: Session, actor: User, target: User) -> bool:
    """May `actor` see `target`'s personal data (payments, presence, ...)?"""
    if actor.role == UserRole.admin or actor.id == target.id:
        return True
    if actor.role == UserRole.student:
        return False  # students see only themselves
    if actor.role == UserRole.staff:
        return target.faculty_id is not None and target.faculty_id == actor.faculty_id
    # tutor / teacher: target must be a student of one of their groups
    groups = visible_group_ids(db, actor)
    return target.group_id is not None and target.group_id in groups


def ensure_can_access_user(db: Session, actor: User, target: User) -> None:
    """Raise 403 unless can_access_user. Routers call this, not their own checks."""
    if not can_access_user(db, actor, target):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu ma'lumotni ko'rish uchun ruxsatingiz yo'q",
        )
