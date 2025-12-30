from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.user import User, Role

settings = get_settings()


def _decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return subject


async def get_current_user(
    session: AsyncSession = Depends(get_db_session),
    access_token: str | None = Cookie(default=None),
) -> User:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Not authenticated",
            headers={"Location": "/login"},
        )
    subject = _decode_token(access_token)
    result = await session.execute(select(User).where(User.email == subject))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Inactive user",
            headers={"Location": "/login"},
        )
    return user


def require_role(*roles: Role):
    async def _role_guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _role_guard


async def get_current_user_optional(
    session: AsyncSession = Depends(get_db_session),
    access_token: str | None = Cookie(default=None),
) -> User | None:
    """Get current user if logged in, otherwise return None (no redirect)."""
    if not access_token:
        return None
    try:
        payload = jwt.decode(access_token, settings.secret_key, algorithms=["HS256"])
        subject = payload.get("sub")
        if not subject:
            return None
    except JWTError:
        return None
    
    result = await session.execute(select(User).where(User.email == subject))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user
