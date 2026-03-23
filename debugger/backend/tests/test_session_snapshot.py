"""
Regression tests for Comment 4:
  - /analytics/session-summary persists a SessionSnapshot on first call
  - Same-day second call updates the existing row (no duplicate)
"""
import pytest
from datetime import date
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import AnonSession, SessionSnapshot
from app.core.auth import create_access_token


async def _make_session(db):
    anon = AnonSession()
    db.add(anon)
    await db.commit()
    await db.refresh(anon)
    return anon


@pytest.mark.asyncio
async def test_session_summary_creates_snapshot_on_first_call(client: AsyncClient, db_session):
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)

    res = await client.get(
        f"/api/v1/analytics/session-summary?session_id={anon.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200

    rows = (await db_session.execute(
        select(SessionSnapshot).where(SessionSnapshot.session_id == anon.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].date_bucket == date.today().isoformat()


@pytest.mark.asyncio
async def test_session_summary_updates_snapshot_on_same_day_call(client: AsyncClient, db_session):
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)

    # First call
    res1 = await client.get(
        f"/api/v1/analytics/session-summary?session_id={anon.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 200

    # Second call same day
    res2 = await client.get(
        f"/api/v1/analytics/session-summary?session_id={anon.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200

    # Must still be exactly one row — no duplicate inserted
    rows = (await db_session.execute(
        select(SessionSnapshot).where(SessionSnapshot.session_id == anon.id)
    )).scalars().all()
    assert len(rows) == 1
