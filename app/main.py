from collections import deque
from time import monotonic
from typing import Deque

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.init_db import init_db
from app.db.session import Base, engine
import app.models  # noqa: F401
from app.routers import auth, bookings, pages, admin
from app.services.content import get_translations, get_profile

settings = get_settings()

app = FastAPI(title=settings.app_name, default_response_class=ORJSONResponse)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# In-memory, per-process rate limiter.
_rate_limit_store: dict[str, Deque[float]] = {}

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = monotonic()
    window_seconds = settings.rate_limit_window_seconds
    max_requests = settings.rate_limit_max_requests
    timestamps = _rate_limit_store.setdefault(client_ip, deque())

    while timestamps and now - timestamps[0] > window_seconds:
        timestamps.popleft()

    if len(timestamps) >= max_requests:
        return PlainTextResponse("Too many requests", status_code=429)

    timestamps.append(now)
    return await call_next(request)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers["Content-Security-Policy"] = csp
    
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import RedirectResponse

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Handle redirect exceptions (303 See Other, 307 Temporary Redirect, etc.)
    if exc.status_code in (301, 302, 303, 307, 308):
        location = None
        if hasattr(exc, 'headers') and exc.headers:
            location = exc.headers.get("Location")
        if location:
            return RedirectResponse(url=location, status_code=exc.status_code)
    
    lang = request.cookies.get("lang", "ar")
    t = get_translations(lang)
    profile = get_profile(lang)
    
    return templates.TemplateResponse(
        "errors/error.html",
        {
            "request": request,
            "t": t,
            "profile": profile,
            "current_user": None,
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
            "code": exc.status_code,
            "title": t['404_title'] if exc.status_code == 404 else "Error",
            "message": exc.detail if exc.detail else t.get('404_message', 'An error occurred'),
        },
        status_code=exc.status_code
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    lang = request.cookies.get("lang", "ar")
    t = get_translations(lang)
    profile = get_profile(lang)
    return templates.TemplateResponse(
        "errors/error.html",
        {
            "request": request,
            "t": t,
            "profile": profile,
            "current_user": None,
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
            "code": 500,
            "title": "Error",
            "message": t.get('error_message', 'An unexpected error occurred'),
        },
        status_code=500
    )

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(bookings.router)
app.include_router(admin.router)


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.auto_create_db:
        async with AsyncSession(engine) as session:
            await init_db(session)
