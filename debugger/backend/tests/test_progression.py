"""
Regression tests for:
  - Comment 1: Hint and solution direct API bypass of reflection/tier prerequisites
  - Comment 2: Hint tier progression and solution reveal across fresh and resumed sessions
  - Comment 5: Whitespace-only submission validation
"""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import (
    AnonSession, CodeSubmission, ExecutionResult, ErrorRecord,
    HintSequence, ReflectionResponse, HintEvent,
)
from app.core.auth import create_access_token


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

async def _make_session(db):
    anon = AnonSession()
    db.add(anon)
    await db.commit()
    await db.refresh(anon)
    return anon


async def _make_submission_with_error(db, session_id, concept="Variable Initialization"):
    sub = CodeSubmission(code_text="x = y", session_id=session_id)
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    exec_res = ExecutionResult(
        submission_id=sub.id, stdout="", stderr="err", traceback="NameError: y",
        execution_time=0.1, success_flag=False, timed_out=False, exit_code=1,
    )
    db.add(exec_res)
    await db.commit()
    await db.refresh(exec_res)

    err = ErrorRecord(
        execution_result_id=exec_res.id,
        exception_type="NameError",
        concept_category=concept,
        cognitive_skill="State awareness",
        failed_attempts=1,
    )
    db.add(err)
    await db.commit()
    return sub


async def _seed_hints(db, concept="Variable Initialization"):
    for tier, name in [(1, "Nudge"), (2, "Guidance"), (3, "Solution")]:
        db.add(HintSequence(
            concept_category=concept, tier=tier,
            tier_name=name, hint_text=f"Hint tier {tier} for {concept}",
        ))
    await db.commit()


async def _add_reflection(db, submission_id):
    r = ReflectionResponse(submission_id=submission_id, response_text="I see.", hint_unlocked=True)
    db.add(r)
    await db.commit()
    return r


async def _add_hint_events(db, submission_id, session_id, tiers: list):
    """Persist explicit tier-keyed HintEvents for the given tiers."""
    for tier in tiers:
        db.add(HintEvent(
            submission_id=submission_id,
            session_id=session_id,
            hint_text=f"hint tier {tier}",
            tier=tier,
        ))
    await db.commit()


# ---------------------------------------------------------------------------
# Hint bypass — no reflection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hint_without_reflection_returns_403(client: AsyncClient, db_session):
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)
    sub = await _make_submission_with_error(db_session, anon.id)
    await _seed_hints(db_session)

    res = await client.post(
        "/api/v1/hint",
        json={"submission_id": str(sub.id), "tier": 1, "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "reflection" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_hint_tier_skip_returns_403(client: AsyncClient, db_session):
    """Requesting tier 2 without having received tier 1 must be rejected."""
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)
    sub = await _make_submission_with_error(db_session, anon.id)
    await _seed_hints(db_session)
    await _add_reflection(db_session, sub.id)
    # No HintEvents — tier 1 not yet served

    res = await client.post(
        "/api/v1/hint",
        json={"submission_id": str(sub.id), "tier": 2, "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "tier 1" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_hint_tier1_allowed_after_reflection(client: AsyncClient, db_session):
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)
    sub = await _make_submission_with_error(db_session, anon.id)
    await _seed_hints(db_session)
    await _add_reflection(db_session, sub.id)

    res = await client.post(
        "/api/v1/hint",
        json={"submission_id": str(sub.id), "tier": 1, "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["tier"] == 1


@pytest.mark.asyncio
async def test_hint_tier2_allowed_after_tier1_event(client: AsyncClient, db_session):
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)
    sub = await _make_submission_with_error(db_session, anon.id)
    await _seed_hints(db_session)
    await _add_reflection(db_session, sub.id)
    await _add_hint_events(db_session, sub.id, anon.id, tiers=[1])

    res = await client.post(
        "/api/v1/hint",
        json={"submission_id": str(sub.id), "tier": 2, "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["tier"] == 2


@pytest.mark.asyncio
async def test_hint_tier1_idempotent(client: AsyncClient, db_session):
    """Requesting tier 1 again after it was already served must return 200 (idempotent)."""
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)
    sub = await _make_submission_with_error(db_session, anon.id)
    await _seed_hints(db_session)
    await _add_reflection(db_session, sub.id)
    await _add_hint_events(db_session, sub.id, anon.id, tiers=[1])

    res = await client.post(
        "/api/v1/hint",
        json={"submission_id": str(sub.id), "tier": 1, "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["tier"] == 1


# ---------------------------------------------------------------------------
# Solution bypass — no reflection / no tier-3 unlock
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_solution_without_reflection_returns_403(client: AsyncClient, db_session):
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)
    sub = await _make_submission_with_error(db_session, anon.id)
    await _seed_hints(db_session)

    res = await client.post(
        "/api/v1/solution-request",
        json={"submission_id": str(sub.id), "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "reflection" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_solution_without_tier3_unlock_returns_403(client: AsyncClient, db_session):
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)
    sub = await _make_submission_with_error(db_session, anon.id)
    await _seed_hints(db_session)
    await _add_reflection(db_session, sub.id)
    # Tiers 1 and 2 served — tier 3 not yet unlocked
    await _add_hint_events(db_session, sub.id, anon.id, tiers=[1, 2])

    res = await client.post(
        "/api/v1/solution-request",
        json={"submission_id": str(sub.id), "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "hint" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_solution_allowed_after_all_prerequisites(client: AsyncClient, db_session):
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)
    sub = await _make_submission_with_error(db_session, anon.id)
    await _seed_hints(db_session)
    await _add_reflection(db_session, sub.id)
    await _add_hint_events(db_session, sub.id, anon.id, tiers=[1, 2, 3])

    res = await client.post(
        "/api/v1/solution-request",
        json={"submission_id": str(sub.id), "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_solution_reveal_across_resumed_session(client: AsyncClient, db_session):
    """After a page refresh (new client, same DB state), solution must still be
    accessible when tier-3 HintEvent already exists and solution was revealed."""
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)
    sub = await _make_submission_with_error(db_session, anon.id)
    await _seed_hints(db_session)
    await _add_reflection(db_session, sub.id)
    await _add_hint_events(db_session, sub.id, anon.id, tiers=[1, 2, 3])

    # Simulate 3 solution requests to trigger reveal
    last_res = None
    for _ in range(3):
        last_res = await client.post(
            "/api/v1/solution-request",
            json={"submission_id": str(sub.id), "session_id": str(anon.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert last_res.status_code == 200

    assert last_res.json()["solution_revealed"] is True
    assert last_res.json()["solution_text"] is not None

    # Resumed session: GET state endpoint must reflect revealed solution
    state_res = await client.get(
        f"/api/v1/solution-request/{sub.id}?session_id={anon.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert state_res.status_code == 200
    assert state_res.json()["solution_revealed"] is True


# ---------------------------------------------------------------------------
# Whitespace-only submission
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_whitespace_only_code_returns_422(client: AsyncClient, db_session):
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)

    for payload in ["   ", "\t\n", "\n\n\n"]:
        res = await client.post(
            "/api/v1/execute",
            json={"code": payload, "language": "python", "session_id": str(anon.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 422, f"Expected 422 for code={repr(payload)}"
        detail = str(res.json())
        assert "whitespace" in detail.lower() or "empty" in detail.lower()


@pytest.mark.asyncio
async def test_valid_code_is_not_rejected(client: AsyncClient, db_session):
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)

    with patch("app.api.v1.routes.execute.execute_code", return_value=type("R", (), {
        "stdout": "1", "stderr": "", "traceback": "", "execution_time": 0.01,
        "success": True, "timed_out": False, "exit_code": 0,
    })()):
        res = await client.post(
            "/api/v1/execute",
            json={"code": "print(1)", "language": "python", "session_id": str(anon.id)},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Comment 1 regression: null-tier legacy HintEvent must not crash hint endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hint_with_null_tier_legacy_row_does_not_500(client: AsyncClient, db_session):
    """A pre-existing null-tier HintEvent (written by execute before the fix)
    must be ignored by the progression gate so tier 1 is still serveable
    without a 500 or a spurious 403."""
    anon = await _make_session(db_session)
    token = create_access_token(str(anon.id), is_anon=True)
    sub = await _make_submission_with_error(db_session, anon.id)
    await _seed_hints(db_session)
    await _add_reflection(db_session, sub.id)

    # Simulate the legacy execute path: HintEvent with tier=None
    db_session.add(HintEvent(
        submission_id=sub.id,
        session_id=anon.id,
        hint_text="contextual hint from execute",
        tier=None,
    ))
    await db_session.commit()

    res = await client.post(
        "/api/v1/hint",
        json={"submission_id": str(sub.id), "tier": 1, "session_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["tier"] == 1
