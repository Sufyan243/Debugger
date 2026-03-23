"""
Migration-aware regression tests.

These tests run the full Alembic migration chain against a real (file-based)
SQLite database and then exercise the hint/solution route logic against that
upgraded schema — catching any drift between ORM models and migration files
before it reaches production.

Separate from the in-memory conftest fixtures so that Base.metadata.create_all
(which always reflects the current ORM) cannot mask missing migrations.
"""
import os
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock

from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
from httpx import AsyncClient, ASGITransport
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db.session import get_db
from app.db.models import AnonSession, CodeSubmission, ExecutionResult, ErrorRecord, HintSequence, ReflectionResponse, HintEvent
from app.core.auth import create_access_token

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BACKEND_DIR = Path(__file__).parent.parent
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"
_VERSIONS_DIR = _BACKEND_DIR / "alembic" / "versions"


# ---------------------------------------------------------------------------
# Alembic-migrated DB fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def migrated_db(tmp_path):
    """
    Yields an AsyncSession backed by a SQLite DB that has been brought to HEAD
    via the real Alembic migration chain — not Base.metadata.create_all.
    """
    db_file = tmp_path / "test_migrated.db"
    db_url_sync = f"sqlite:///{db_file}"
    db_url_async = f"sqlite+aiosqlite:///{db_file}"

    # Run all migrations synchronously (Alembic uses sync engine internally).
    cfg = AlembicConfig(str(_ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", db_url_sync)
    alembic_command.upgrade(cfg, "head")

    engine = create_async_engine(db_url_async, connect_args={"check_same_thread": False})
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session, engine

    await engine.dispose()
    if db_file.exists():
        db_file.unlink()


@pytest_asyncio.fixture(scope="function")
async def migrated_client(migrated_db):
    """AsyncClient wired to the migrated DB session."""
    session, _ = migrated_db

    async def override_get_db():
        yield session

    try:
        import fakeredis.aioredis as fakeredis_async
        fake_redis = fakeredis_async.FakeRedis(decode_responses=True)
    except ImportError:
        fake_redis = _build_mock_redis()

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.core.redis_client.get_redis", return_value=fake_redis):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac, session
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Schema drift guards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hint_events_tier_column_exists_after_migration(migrated_db):
    """Migration 012 must add the `tier` column to hint_events."""
    _, engine = migrated_db
    async with engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: [
                col["name"] for col in inspect(sync_conn).get_columns("hint_events")
            ]
        )
    assert "tier" in columns, (
        "hint_events.tier column missing — migration 012 may not have run. "
        "Run: alembic upgrade head"
    )


@pytest.mark.asyncio
async def test_hint_events_tier_column_is_nullable(migrated_db):
    """hint_events.tier must be nullable so existing rows are unaffected."""
    _, engine = migrated_db
    async with engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: {
                col["name"]: col
                for col in inspect(sync_conn).get_columns("hint_events")
            }
        )
    tier_col = columns.get("tier")
    assert tier_col is not None
    assert tier_col["nullable"] is True, "hint_events.tier must be nullable"


@pytest.mark.asyncio
async def test_uq_users_username_constraint_absent_after_migration(migrated_db):
    """Migration 012 must drop uq_users_username from the users table."""
    _, engine = migrated_db
    async with engine.connect() as conn:
        unique_constraints = await conn.run_sync(
            lambda sync_conn: [
                uc["name"] for uc in inspect(sync_conn).get_unique_constraints("users")
            ]
        )
    assert "uq_users_username" not in unique_constraints, (
        "uq_users_username still present — migration 012 downgrade/upgrade may be broken."
    )


@pytest.mark.asyncio
async def test_alembic_head_matches_orm_tables(migrated_db):
    """All ORM-declared tables must exist in the migrated DB."""
    from app.db.models import Base
    _, engine = migrated_db
    async with engine.connect() as conn:
        existing = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
    orm_tables = set(Base.metadata.tables.keys())
    missing = orm_tables - set(existing)
    assert not missing, (
        f"Tables declared in ORM models are missing from migrated DB: {missing}. "
        "Add a migration for any new model."
    )


# ---------------------------------------------------------------------------
# Route logic against migrated schema
# ---------------------------------------------------------------------------

async def _setup_submission(session, concept="Variable Initialization"):
    """Seed a full submission chain and return (anon, sub, token)."""
    anon = AnonSession()
    session.add(anon)
    await session.commit()
    await session.refresh(anon)

    sub = CodeSubmission(code_text="x = y", session_id=anon.id)
    session.add(sub)
    await session.commit()
    await session.refresh(sub)

    exec_res = ExecutionResult(
        submission_id=sub.id, stdout="", stderr="err", traceback="NameError",
        execution_time=0.1, success_flag=False, timed_out=False, exit_code=1,
    )
    session.add(exec_res)
    await session.commit()
    await session.refresh(exec_res)

    err = ErrorRecord(
        execution_result_id=exec_res.id,
        exception_type="NameError",
        concept_category=concept,
        cognitive_skill="State awareness",
        failed_attempts=1,
    )
    session.add(err)
    await session.commit()

    for tier, name in [(1, "Nudge"), (2, "Guidance"), (3, "Solution")]:
        session.add(HintSequence(
            concept_category=concept, tier=tier,
            tier_name=name, hint_text=f"Hint tier {tier}",
        ))
    await session.commit()

    token = create_access_token(str(anon.id), is_anon=True)
    return anon, sub, token


@pytest.mark.asyncio
async def test_hint_tier_write_and_read_on_migrated_schema(migrated_client):
    """
    Serving a hint must persist HintEvent.tier on the migrated schema
    (not just on a freshly created schema via create_all).
    """
    client, session = migrated_client
    anon, sub, token = await _setup_submission(session)

    # Add reflection
    session.add(ReflectionResponse(submission_id=sub.id, response_text="ok", hint_unlocked=True))
    await session.commit()

    res = await client.post(
        "/api/v1/hint",
        json={"submission_id": str(sub.id), "tier": 1, "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["tier"] == 1

    # Verify the HintEvent row was persisted with tier=1 in the migrated DB
    from sqlalchemy import select
    result = await session.execute(
        select(HintEvent).where(
            HintEvent.submission_id == sub.id,
            HintEvent.tier == 1,
        )
    )
    event = result.scalars().first()
    assert event is not None, "HintEvent with tier=1 was not persisted on migrated schema"
    assert event.tier == 1


@pytest.mark.asyncio
async def test_solution_tier3_gate_on_migrated_schema(migrated_client):
    """
    _has_tier3_unlocked must correctly query HintEvent.tier on the migrated
    schema — not only on a freshly created schema.
    """
    from sqlalchemy import select
    client, session = migrated_client
    anon, sub, token = await _setup_submission(session)

    session.add(ReflectionResponse(submission_id=sub.id, response_text="ok", hint_unlocked=True))
    await session.commit()

    # Seed tier-1 and tier-2 events directly (bypassing the hint route)
    for t in [1, 2]:
        session.add(HintEvent(
            submission_id=sub.id, session_id=anon.id,
            hint_text=f"hint {t}", tier=t,
        ))
    await session.commit()

    # Solution must be blocked — tier-3 not yet unlocked
    res = await client.post(
        "/api/v1/solution-request",
        json={"submission_id": str(sub.id), "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403

    # Seed tier-3 event
    session.add(HintEvent(
        submission_id=sub.id, session_id=anon.id,
        hint_text="hint 3", tier=3,
    ))
    await session.commit()

    # Solution must now be accessible
    res = await client.post(
        "/api/v1/solution-request",
        json={"submission_id": str(sub.id), "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_duplicate_username_allowed_on_migrated_schema(migrated_db):
    """
    After migration 012 drops uq_users_username, inserting two users with
    the same username must succeed on the migrated schema.
    """
    from app.db.models import User
    session, _ = migrated_db

    u1 = User(email="a@example.com", username="shared", provider="github", provider_id="gh_1")
    u2 = User(email="b@example.com", username="shared", provider="github", provider_id="gh_2")
    session.add(u1)
    session.add(u2)
    await session.commit()  # must not raise IntegrityError

    from sqlalchemy import select
    result = await session.execute(select(User).where(User.username == "shared"))
    assert len(result.scalars().all()) == 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_mock_redis():
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
