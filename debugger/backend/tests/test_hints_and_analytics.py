"""
Regression tests for:
  - Comment 4: Hint tier progression across all seeded concept categories
  - Comment 8: Success streak calculation under mixed-concept failure/success timelines
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import (
    CodeSubmission, ExecutionResult, ErrorRecord,
    HintSequence, ConceptCategory,
)
from app.db.seed import run_seed, run_hint_seed
from app.intelligence.analytics_service import get_concept_stats


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def seed(db_session):
    """Seed concept categories and hint sequences before every test."""
    await run_seed(db_session)
    await run_hint_seed(db_session)


# ---------------------------------------------------------------------------
# Comment 4: Hint tier coverage
# ---------------------------------------------------------------------------

ALL_CONCEPTS = [
    "Variable Initialization",
    "Typo / Spelling",
    "Data Type Compatibility",
    "Object Attributes",
    "Value Validity",
    "List Management",
    "Dictionary Usage",
    "Syntax",
    "Mathematical Operations",
    "Module Usage",
    "Recursion",
    "Runtime Behaviour",
    "Iteration",
    "Resource Management",
    "File I/O",
    "String Encoding",
    "Assertions",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("concept", ALL_CONCEPTS)
async def test_all_three_tiers_exist_for_concept(concept, db_session):
    """Every concept category must have tier 1, 2, and 3 hints seeded."""
    for tier in (1, 2, 3):
        result = await db_session.execute(
            select(HintSequence).where(
                HintSequence.concept_category == concept,
                HintSequence.tier == tier,
            )
        )
        hint = result.scalar_one_or_none()
        assert hint is not None, (
            f"Missing tier {tier} hint for concept '{concept}'. "
            "Add it to run_hint_seed() in seed.py."
        )
        assert hint.hint_text.strip(), f"Tier {tier} hint for '{concept}' has empty text."


@pytest.mark.asyncio
async def test_hint_route_fallback_returns_lower_tier(client: AsyncClient, db_session):
    """
    When the exact requested tier is missing, the hint endpoint must return
    the nearest lower tier rather than 404.
    """
    import uuid
    from app.db.models import AnonSession
    from app.core.auth import create_access_token

    # Create anon session
    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)
    token = create_access_token(str(anon.id), is_anon=True)
    session_id = str(anon.id)

    # Create submission + execution result + error record for a known concept
    sub = CodeSubmission(code_text="x = y", session_id=anon.id)
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)

    exec_res = ExecutionResult(
        submission_id=sub.id, stdout="", stderr="err", traceback="err",
        execution_time=0.1, success_flag=False, timed_out=False, exit_code=1,
    )
    db_session.add(exec_res)
    await db_session.commit()
    await db_session.refresh(exec_res)

    err = ErrorRecord(
        execution_result_id=exec_res.id,
        exception_type="NameError",
        concept_category="Variable Initialization",
        cognitive_skill="State awareness",
        failed_attempts=1,
    )
    db_session.add(err)
    await db_session.commit()

    # Delete tier 2 to simulate a missing tier
    tier2 = (await db_session.execute(
        select(HintSequence).where(
            HintSequence.concept_category == "Variable Initialization",
            HintSequence.tier == 2,
        )
    )).scalar_one_or_none()
    if tier2:
        await db_session.delete(tier2)
        await db_session.commit()

    # Request tier 2 — should fall back to tier 1
    res = await client.post(
        "/api/v1/hint",
        json={"submission_id": str(sub.id), "tier": 2, "session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tier"] == 1  # fell back to tier 1


# ---------------------------------------------------------------------------
# Comment 8: Streak calculation correctness
# ---------------------------------------------------------------------------

async def _make_submission(db, session_id, code, success, concept=None, ts=None):
    """Helper: create a submission + execution result + optional error record."""
    sub = CodeSubmission(
        code_text=code,
        session_id=session_id,
        timestamp=ts or datetime.now(timezone.utc),
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    exec_res = ExecutionResult(
        submission_id=sub.id,
        stdout="ok" if success else "",
        stderr="" if success else "err",
        traceback="" if success else "err",
        execution_time=0.1,
        success_flag=success,
        timed_out=False,
        exit_code=0 if success else 1,
    )
    db.add(exec_res)
    await db.commit()
    await db.refresh(exec_res)

    if concept and not success:
        err = ErrorRecord(
            execution_result_id=exec_res.id,
            exception_type="Error",
            concept_category=concept,
            cognitive_skill="reasoning",
            failed_attempts=1,
        )
        db.add(err)
        await db.commit()

    return sub


@pytest.mark.asyncio
async def test_streak_is_zero_when_last_submission_failed(db_session):
    import uuid
    session_id = uuid.uuid4()
    base = datetime.now(timezone.utc)

    await _make_submission(db_session, session_id, "a", False, "Variable Initialization",
                           ts=base - timedelta(seconds=2))
    await _make_submission(db_session, session_id, "b", False, "Variable Initialization",
                           ts=base - timedelta(seconds=1))

    stats = await get_concept_stats(session_id, db_session)
    vi = next((s for s in stats if s["concept"] == "Variable Initialization"), None)
    assert vi is not None
    assert vi["success_streak"] == 0


@pytest.mark.asyncio
async def test_streak_counts_consecutive_successes(db_session):
    import uuid
    session_id = uuid.uuid4()
    base = datetime.now(timezone.utc)

    await _make_submission(db_session, session_id, "a", False, "Variable Initialization",
                           ts=base - timedelta(seconds=3))
    await _make_submission(db_session, session_id, "b", True, ts=base - timedelta(seconds=2))
    await _make_submission(db_session, session_id, "c", True, ts=base - timedelta(seconds=1))

    stats = await get_concept_stats(session_id, db_session)
    vi = next((s for s in stats if s["concept"] == "Variable Initialization"), None)
    assert vi is not None
    assert vi["success_streak"] == 2


@pytest.mark.asyncio
async def test_unrelated_concept_failure_does_not_break_streak(db_session):
    """
    A TypeError failure should NOT break the NameError/Variable Initialization streak.
    """
    import uuid
    session_id = uuid.uuid4()
    base = datetime.now(timezone.utc)

    # NameError failure
    await _make_submission(db_session, session_id, "a", False, "Variable Initialization",
                           ts=base - timedelta(seconds=4))
    # Success
    await _make_submission(db_session, session_id, "b", True, ts=base - timedelta(seconds=3))
    # Unrelated TypeError failure — must NOT break Variable Initialization streak
    await _make_submission(db_session, session_id, "c", False, "Data Type Compatibility",
                           ts=base - timedelta(seconds=2))
    # Another success
    await _make_submission(db_session, session_id, "d", True, ts=base - timedelta(seconds=1))

    stats = await get_concept_stats(session_id, db_session)
    vi = next((s for s in stats if s["concept"] == "Variable Initialization"), None)
    assert vi is not None
    # Two consecutive successes at the end; the TypeError in between does not break it
    assert vi["success_streak"] == 2


@pytest.mark.asyncio
async def test_streak_resets_when_same_concept_fails_again(db_session):
    import uuid
    session_id = uuid.uuid4()
    base = datetime.now(timezone.utc)

    await _make_submission(db_session, session_id, "a", False, "Variable Initialization",
                           ts=base - timedelta(seconds=4))
    await _make_submission(db_session, session_id, "b", True, ts=base - timedelta(seconds=3))
    await _make_submission(db_session, session_id, "c", True, ts=base - timedelta(seconds=2))
    # Same concept fails again — streak must reset
    await _make_submission(db_session, session_id, "d", False, "Variable Initialization",
                           ts=base - timedelta(seconds=1))

    stats = await get_concept_stats(session_id, db_session)
    vi = next((s for s in stats if s["concept"] == "Variable Initialization"), None)
    assert vi is not None
    assert vi["success_streak"] == 0
