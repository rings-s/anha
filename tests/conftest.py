import asyncio
import importlib
import os

import pytest
from sqlalchemy import text


def _run(coro):
    return asyncio.run(coro)


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_file(path: str = ".env") -> dict[str, str]:
    if not os.path.exists(path):
        return {}
    values: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            values[key] = value
    return values


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    env_values = _load_env_file()
    
    # Try PostgreSQL first, fall back to SQLite
    test_db_url = (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or env_values.get("TEST_DATABASE_URL")
        or env_values.get("DATABASE_URL")
    )
    
    use_sqlite = False
    
    # Check if PostgreSQL is available
    if test_db_url and "postgresql" in test_db_url:
        async def _preflight():
            import asyncpg
            dsn = test_db_url.replace("postgresql+asyncpg", "postgresql", 1)
            ssl_value = _parse_bool(os.environ.get("DB_CONNECT_SSL"))
            kwargs = {"timeout": 5}
            if ssl_value is not None:
                kwargs["ssl"] = ssl_value
            conn = await asyncio.wait_for(asyncpg.connect(dsn, **kwargs), timeout=5)
            await conn.close()

        try:
            _run(_preflight())
        except Exception as exc:
            print(f"PostgreSQL not available ({exc}), falling back to SQLite...")
            use_sqlite = True
    else:
        use_sqlite = True
    
    if use_sqlite:
        # Use a temporary SQLite database for testing
        tmp_dir = tmp_path_factory.mktemp("db")
        test_db_path = tmp_dir / "test.db"
        test_db_url = f"sqlite+aiosqlite:///{test_db_path}"
        print(f"Using SQLite test database: {test_db_url}")
    
    os.environ["DATABASE_URL"] = test_db_url
    os.environ["SECRET_KEY"] = "test-secret"
    os.environ["AUTO_CREATE_DB"] = "true"
    os.environ["DB_CONNECT_TIMEOUT_SECONDS"] = "5"
    os.environ["DB_CONNECT_SSL"] = "false"

    from app.core import config
    config.get_settings.cache_clear()

    import app.db.session as session
    importlib.reload(session)

    import app.main as main
    importlib.reload(main)
    
    # Create tables before returning the app
    async def _create_tables():
        from app.db.session import Base, engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    _run(_create_tables())
    
    return main.app


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def clean_database(app):
    """Clean database before each test. The 'app' dependency ensures tables exist."""
    async def _clean():
        from app.db.session import AsyncSessionLocal, Base
        
        # Check if using SQLite or PostgreSQL
        db_url = os.environ.get("DATABASE_URL", "")
        
        if "sqlite" in db_url:
            # For SQLite, delete all data from tables
            async with AsyncSessionLocal() as session:
                for table in reversed(Base.metadata.sorted_tables):
                    try:
                        await session.execute(table.delete())
                    except Exception:
                        pass  # Table might not exist yet
                await session.commit()
        else:
            # PostgreSQL TRUNCATE
            table_names = [table.name for table in Base.metadata.sorted_tables]
            if not table_names:
                return
            async with AsyncSessionLocal() as session:
                joined = ", ".join(f'"{name}"' for name in table_names)
                await session.execute(text(f"TRUNCATE {joined} CASCADE"))
                await session.commit()

    _run(_clean())


def create_user(email: str, password: str, role: str = "client", is_active: bool = True):
    async def _create():
        from app.core.security import hash_password
        from app.db.session import AsyncSessionLocal
        from app.models.user import Role, User

        async with AsyncSessionLocal() as session:
            user = User(
                email=email,
                full_name=email.split("@")[0],
                phone="",
                hashed_password=hash_password(password),
                role=Role(role),
                is_active=is_active,
            )
            session.add(user)
            await session.commit()
            return user.id

    return _run(_create())


def get_user_by_email(email: str):
    async def _get():
        from sqlalchemy import select
        from app.db.session import AsyncSessionLocal
        from app.models.user import User

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()

    return _run(_get())


def create_service(name_ar: str, price: float):
    async def _create():
        from app.db.session import AsyncSessionLocal
        from app.models.service import Service

        async with AsyncSessionLocal() as session:
            service = Service(name_ar=name_ar, name_en="Test", description="", price=price)
            session.add(service)
            await session.commit()
            return service.id

    return _run(_create())


def get_service_by_id(service_id: int):
    async def _get():
        from sqlalchemy import select
        from app.db.session import AsyncSessionLocal
        from app.models.service import Service

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Service).where(Service.id == service_id))
            return result.scalar_one_or_none()

    return _run(_get())


def get_service_by_name(name_ar: str):
    async def _get():
        from sqlalchemy import select
        from app.db.session import AsyncSessionLocal
        from app.models.service import Service

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Service).where(Service.name_ar == name_ar))
            return result.scalar_one_or_none()

    return _run(_get())


def get_booking_by_contact(contact_name: str):
    async def _get():
        from sqlalchemy import select
        from app.db.session import AsyncSessionLocal
        from app.models.booking import Booking

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Booking).where(Booking.contact_name == contact_name))
            return result.scalar_one_or_none()

    return _run(_get())
