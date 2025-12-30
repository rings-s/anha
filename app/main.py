from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
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
