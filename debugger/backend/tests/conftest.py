import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import patch, AsyncMock
from app.main import app
from app.db.session import get_db
from app.db.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    # Use fakeredis so tests never need a live Redis instance.
    # Falls back to a simple AsyncMock if fakeredis is not installed.
    try:
        import fakeredis.aioredis as fakeredis_async
        fake_redis = fakeredis_async.FakeRedis(decode_responses=True)
    except ImportError:
        # Minimal async mock that satisfies the pipeline/set/get interface
        fake_redis = _build_mock_redis()

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.core.redis_client.get_redis", return_value=fake_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


def _build_mock_redis():
    """Minimal in-memory async Redis stand-in used when fakeredis is absent."""
    store: dict = {}

    class _Pipeline:
        def __init__(self):
            self._cmds = []

        async def get(self, key):
            self._cmds.append(("get", key))
            return self

        async def delete(self, key):
            self._cmds.append(("delete", key))
            return self

        async def execute(self):
            results = []
            for cmd, key in self._cmds:
                if cmd == "get":
                    results.append(store.get(key))
                elif cmd == "delete":
                    store.pop(key, None)
                    results.append(1)
            return results

    class _FakeRedis:
        async def set(self, key, value, ex=None):
            store[key] = value

        async def get(self, key):
            return store.get(key)

        async def delete(self, key):
            store.pop(key, None)

        def pipeline(self):
            return _Pipeline()

    return _FakeRedis()
