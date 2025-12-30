from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# Build connect_args based on database type
connect_args = {}
is_postgresql = "postgresql" in settings.database_url

if is_postgresql:
    # PostgreSQL-specific connection arguments
    if settings.db_connect_timeout_seconds is not None:
        connect_args["timeout"] = settings.db_connect_timeout_seconds
    if settings.db_connect_ssl is not None:
        connect_args["ssl"] = settings.db_connect_ssl
else:
    # SQLite-specific connection arguments
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.database_url,
    future=True,
    echo=False,
    connect_args=connect_args,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
