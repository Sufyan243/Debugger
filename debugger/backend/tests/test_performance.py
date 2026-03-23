"""
Performance and resilience tests for critical backend endpoints.
Thresholds enforced:
  - /auth/login  p95 < 500 ms  (10 sequential calls)
  - /auth/anon   p95 < 300 ms  (10 sequential calls)
  - /execute     p95 < 1000 ms (10 sequential calls, mocked sandbox)
  - Degraded-network: 503 on /execute must return within 2 s
"""
import time
import statistics
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from app.db.models import AnonSession, User
from app.core.auth import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_verified_user(db_session, email="perf@example.com"):
    user = User(
        email=email,
        hashed_password=hash_password("Password1!"),
        provider="email",
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _anon_token(db_session):
    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)
    return create_access_token(str(anon.id), is_anon=True), str(anon.id)


def _p95(samples: list[float]) -> float:
    return statistics.quantiles(sorted(samples), n=100)[94]


# ---------------------------------------------------------------------------
# /auth/anon — 10 sequential calls, p95 < 300 ms
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anon_bootstrap_p95_under_300ms(client: AsyncClient):
    samples = []
    for _ in range(10):
        t0 = time.perf_counter()
        res = await client.post("/api/v1/auth/anon")
        samples.append((time.perf_counter() - t0) * 1000)
        assert res.status_code == 201

    p95 = _p95(samples)
    assert p95 < 300, f"/auth/anon p95={p95:.1f} ms exceeds 300 ms threshold"


# ---------------------------------------------------------------------------
# /auth/login — 10 sequential calls, p95 < 500 ms
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_p95_under_500ms(client: AsyncClient, db_session):
    await _make_verified_user(db_session)
    samples = []
    for _ in range(10):
        t0 = time.perf_counter()
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": "perf@example.com", "password": "Password1!"},
        )
        samples.append((time.perf_counter() - t0) * 1000)
        assert res.status_code == 200

    p95 = _p95(samples)
    assert p95 < 500, f"/auth/login p95={p95:.1f} ms exceeds 500 ms threshold"


# ---------------------------------------------------------------------------
# /execute — 10 sequential calls with mocked sandbox, p95 < 1000 ms
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_p95_under_1000ms(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    mock_result = type("R", (), {
        "stdout": "1\n", "stderr": "", "traceback": "",
        "execution_time": 0.01, "success": True,
        "timed_out": False, "exit_code": 0,
    })()

    samples = []
    with patch("app.api.v1.routes.execute.execute_code", return_value=mock_result):
        for _ in range(10):
            t0 = time.perf_counter()
            res = await client.post(
                "/api/v1/execute",
                json={"code": "print(1)", "language": "python", "session_id": sid},
                headers={"Authorization": f"Bearer {token}"},
            )
            samples.append((time.perf_counter() - t0) * 1000)
            assert res.status_code == 200

    p95 = _p95(samples)
    assert p95 < 1000, f"/execute p95={p95:.1f} ms exceeds 1000 ms threshold"


# ---------------------------------------------------------------------------
# Degraded-network: sandbox timeout → endpoint returns within 2 s
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_sandbox_timeout_returns_within_2s(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)

    async def slow_execute(*args, **kwargs):
        import asyncio
        await asyncio.sleep(0.5)  # simulate slow sandbox
        return type("R", (), {
            "stdout": "", "stderr": "", "traceback": "TimeoutError",
            "execution_time": 0.5, "success": False,
            "timed_out": True, "exit_code": 1,
        })()

    t0 = time.perf_counter()
    with patch("app.api.v1.routes.execute.execute_code", side_effect=slow_execute):
        res = await client.post(
            "/api/v1/execute",
            json={"code": "import time; time.sleep(60)", "language": "python", "session_id": sid},
            headers={"Authorization": f"Bearer {token}"},
        )
    elapsed = (time.perf_counter() - t0) * 1000

    assert res.status_code != 500
    assert elapsed < 2000, f"Slow sandbox response took {elapsed:.0f} ms, threshold 2000 ms"


# ---------------------------------------------------------------------------
# Resilience: Redis unavailable on /auth/anon must not 500
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anon_bootstrap_redis_down_does_not_500(client: AsyncClient):
    from redis.exceptions import RedisError
    with patch("app.core.redis_client.get_redis", side_effect=RedisError("down")):
        res = await client.post("/api/v1/auth/anon")
    # May return 503 (graceful) but must never be 500
    assert res.status_code != 500
