"""Auth endpoints: login (JWT), me, logout + a permanent RBAC sample endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.passwords import verify_password
from app.auth.rbac import create_access_token, get_current_user, require_role
from app.db import get_db
from app.models import User, UserRole
from app.schemas import LoginIn, OkOut, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )
    return TokenOut(access_token=create_access_token(user), user=user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout", response_model=OkOut)
def logout(user: User = Depends(get_current_user)) -> OkOut:
    # Stateless JWT: the client simply discards the token.
    return OkOut()


@router.get(
    "/test-staff-only",
    response_model=OkOut,
    dependencies=[Depends(require_role(UserRole.staff))],
)
def test_staff_only() -> OkOut:
    """Permanent RBAC sample: staff (and admin) only — used by S2 tests."""
    return OkOut()
