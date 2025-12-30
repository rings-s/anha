from datetime import datetime, timedelta
import hashlib

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, create_reset_token, hash_password, verify_password
from app.db.session import get_db_session
from app.models.password_reset import PasswordResetToken
from app.models.user import User, Role
from app.services.content import get_translations

router = APIRouter()
settings = get_settings()


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


@router.post("/register")
async def register(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(""),
    role: str = Form("client"),  # Ignored - always set to client
    session: AsyncSession = Depends(get_db_session),
):
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن لا تقل عن 8 أحرف")
    
    exists = await session.execute(select(User).where(User.email == email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="البريد الإلكتروني مستخدم بالفعل")
    
    # SECURITY: Public registration is CLIENT-ONLY
    # Staff roles (employee, driver, technical, admin) must be created by admin
    user = User(
        email=email,
        full_name=full_name,
        phone=phone,
        hashed_password=hash_password(password),
        role=Role.client,  # Always client for self-registration
        is_active=True,
    )
    session.add(user)
    await session.commit()
    response = _redirect("/dashboard")
    is_secure = settings.environment == "production"
    response.set_cookie(
        "access_token", 
        create_access_token(email), 
        httponly=True, 
        samesite="lax",
        secure=is_secure
    )
    return response


@router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة")
    
    # Role-based redirect
    if user.role == Role.admin:
        redirect_url = "/admin"
    else:
        redirect_url = "/dashboard"
    
    response = _redirect(redirect_url)
    is_secure = settings.environment == "production"
    response.set_cookie(
        "access_token", 
        create_access_token(user.email), 
        httponly=True, 
        samesite="lax",
        secure=is_secure
    )
    return response


@router.post("/logout")
async def logout():
    response = _redirect("/")
    response.delete_cookie("access_token")
    return response


@router.post("/reset/request", response_class=HTMLResponse)
async def reset_request(
    email: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    reset_link = None
    if user:
        token, token_hash = create_reset_token()
        expires_at = datetime.utcnow() + timedelta(minutes=settings.reset_token_expire_minutes)
        session.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
        await session.commit()
        # Direct redirect for demo purposes (skipping email)
        return RedirectResponse(f"/reset/{token}", status_code=303)
    
    # If user not found
    raise HTTPException(status_code=404, detail="Email not found")


@router.post("/reset/confirm")
async def reset_confirm(
    token: str = Form(...),
    new_password: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
):
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="كلمة المرور الجديدة يجب أن لا تقل عن 8 أحرف")
    
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    result = await session.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    matched = result.scalar_one_or_none()
    if not matched or matched.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="الرابط غير صالح أو منتهي")

    user_result = await session.execute(select(User).where(User.id == matched.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    user.hashed_password = hash_password(new_password)
    await session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    await session.commit()
    response = _redirect("/login")
    return response
