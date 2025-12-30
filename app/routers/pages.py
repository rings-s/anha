from datetime import datetime
import hashlib
from fastapi import APIRouter, Cookie, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.service import Service
from app.services.content import get_translations, get_profile
from app.services.deps import get_current_user, get_current_user_optional
from app.models.user import User, Role
from app.models.password_reset import PasswordResetToken

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def _get_lang(request: Request) -> str:
    """Get language from cookie, default to Arabic."""
    return request.cookies.get("lang", "ar")


def _base_context(request: Request, user: User | None = None) -> dict:
    lang = _get_lang(request)
    return {
        "request": request,
        "t": get_translations(lang),
        "profile": get_profile(lang),
        "current_user": user,
        "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr",
    }


@router.get("/set-lang/{lang}", response_class=HTMLResponse)
async def set_language(lang: str, request: Request):
    """Set language preference and redirect back."""
    if lang not in ("ar", "en"):
        lang = "ar"
    
    # Get referer or default to home
    referer = request.headers.get("referer", "/")
    response = RedirectResponse(url=referer, status_code=303)
    response.set_cookie("lang", lang, max_age=60*60*24*365, httponly=True, samesite="lax")
    return response


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    services = (await session.execute(select(Service))).scalars().all()
    context = _base_context(request, user=current_user)
    context["services"] = services
    return templates.TemplateResponse("index.html", context)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", _base_context(request))


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse("register.html", _base_context(request))


@router.get("/reset", response_class=HTMLResponse)
async def reset_request_page(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse("reset_request.html", _base_context(request))


@router.get("/reset/verify/{token}", response_class=HTMLResponse)
async def reset_verify_page(request: Request, token: str, session: AsyncSession = Depends(get_db_session)):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    result = await session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    matched = result.scalar_one_or_none()

    if not matched:
        raise HTTPException(status_code=400, detail="الرابط غير صالح")

    if matched.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="رابط إعادة التعيين منتهي الصلاحية")

    context = _base_context(request)
    context["token"] = token
    return templates.TemplateResponse("reset_verified.html", context)


@router.get("/reset/{token}", response_class=HTMLResponse)
async def reset_confirm_page(request: Request, token: str, session: AsyncSession = Depends(get_db_session)):
    # Verify token exists and is not expired
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    result = await session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    matched = result.scalar_one_or_none()
    
    if not matched:
        raise HTTPException(status_code=400, detail="الرابط غير صالح")
    
    if matched.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="رابط إعادة التعيين منتهي الصلاحية")

    context = _base_context(request)
    context["token"] = token
    return templates.TemplateResponse("reset_confirm.html", context)


@router.get("/reset/sent", response_class=HTMLResponse)
async def reset_sent_page(request: Request):
    return templates.TemplateResponse("reset_success.html", _base_context(request))


@router.get("/reset/done", response_class=HTMLResponse)
async def reset_done_page(request: Request):
    return templates.TemplateResponse("password_updated.html", _base_context(request))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    from app.models.booking import Booking, BookingStatus

    # Basic stats
    if user.role in {Role.employee, Role.technical, Role.driver}:
        q = select(Booking)
    else:
        q = select(Booking).where(Booking.client_id == user.id)

    res = await session.execute(q)
    bookings = res.scalars().all()

    stats = {
        "total": len(bookings),
        "active": len([b for b in bookings if b.status in {BookingStatus.requested, BookingStatus.assigned, BookingStatus.in_progress}]),
        "completed": len([b for b in bookings if b.status == BookingStatus.completed]),
    }

    context = _base_context(request, user=user)
    context["stats"] = stats
    return templates.TemplateResponse("dashboard.html", context)


@router.get("/book", response_class=HTMLResponse)
async def booking_page(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    services = (await session.execute(select(Service))).scalars().all()
    context = _base_context(request, user=user)
    context["services"] = services
    return templates.TemplateResponse("booking.html", context)


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: User = Depends(get_current_user)):
    context = _base_context(request, user=user)
    return templates.TemplateResponse("profile.html", context)


@router.get("/robots.txt")
async def robots_txt():
    content = "User-agent: *\nAllow: /\nSitemap: /sitemap.xml"
    return HTMLResponse(content=content, media_type="text/plain")


@router.get("/sitemap.xml")
async def sitemap_xml(request: Request):
    urls = ["/", "/login", "/register", "/book"]
    base_url = str(request.base_url).rstrip("/")
    
    xml_items = []
    for url in urls:
        xml_items.append(f"<url><loc>{base_url}{url}</loc><changefreq>weekly</changefreq></url>")
    
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{''.join(xml_items)}"
        '</urlset>'
    )
    return HTMLResponse(content=content, media_type="application/xml")
