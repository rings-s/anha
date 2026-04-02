from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# ── Normalise DATABASE_URL ─────────────────────────────────────────────
# Railway (and most PaaS) provide postgres:// or postgresql:// — asyncpg
# requires the postgresql+asyncpg:// scheme.
_raw_url = settings.database_url
if _raw_url.startswith("postgres://"):
    _db_url = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql://") and "+asyncpg" not in _raw_url:
    _db_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    _db_url = _raw_url

is_postgresql = "postgresql" in _db_url

# ── Connection arguments ───────────────────────────────────────────────
connect_args: dict = {}
if is_postgresql:
    if settings.db_connect_timeout_seconds is not None:
        connect_args["timeout"] = settings.db_connect_timeout_seconds
    if settings.db_connect_ssl is not None:
        connect_args["ssl"] = settings.db_connect_ssl
else:
    connect_args["check_same_thread"] = False

# ── Engine ─────────────────────────────────────────────────────────────
# pool_size / max_overflow only valid for PostgreSQL (SQLite uses NullPool)
_engine_kwargs: dict = {
    "future": True,
    "echo": False,
    "connect_args": connect_args,
    "pool_pre_ping": True,
}
if is_postgresql:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine = create_async_engine(_db_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
