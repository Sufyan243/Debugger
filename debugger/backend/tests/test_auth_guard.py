"""
Regression tests for Comment 2:
  Missing or malformed Authorization header must yield 401, not 422,
  across all protected endpoints.
"""
import pytest
from httpx import AsyncClient
from app.db.models import AnonSession
from app.core.auth import create_access_token

PROTECTED_ENDPOINTS = [
    ("POST", "/api/v1/execute",         {"code": "print(1)", "language": "python", "session_id": "00000000-0000-0000-0000-000000000001"}),
    ("POST", "/api/v1/hint",            {"submission_id": "00000000-0000-0000-0000-000000000001", "tier": 1, "session_id": "00000000-0000-0000-0000-000000000001"}),
    ("POST", "/api/v1/reflect",         {"submission_id": "00000000-0000-0000-0000-000000000001", "response_text": "ok", "session_id": "00000000-0000-0000-0000-000000000001"}),
    ("POST", "/api/v1/solution-request",{"submission_id": "00000000-0000-0000-0000-000000000001", "session_id": "00000000-0000-0000-0000-000000000001"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,url,body", PROTECTED_ENDPOINTS)
async def test_missing_authorization_header_returns_401(
    client: AsyncClient, method: str, url: str, body: dict
):
    """No Authorization header must yield 401, not 422."""
    res = await client.request(method, url, json=body)
    assert res.status_code == 401, (
        f"{method} {url} returned {res.status_code}, expected 401 on missing header"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method,url,body", PROTECTED_ENDPOINTS)
async def test_malformed_bearer_returns_401(
    client: AsyncClient, method: str, url: str, body: dict
):
    """Malformed bearer (no 'Bearer ' prefix) must yield 401."""
    res = await client.request(method, url, json=body, headers={"Authorization": "Token abc123"})
    assert res.status_code == 401, (
        f"{method} {url} returned {res.status_code}, expected 401 on malformed bearer"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method,url,body", PROTECTED_ENDPOINTS)
async def test_invalid_jwt_returns_401(
    client: AsyncClient, method: str, url: str, body: dict
):
    """A syntactically valid Bearer prefix but invalid JWT must yield 401."""
    res = await client.request(method, url, json=body, headers={"Authorization": "Bearer not.a.real.token"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_valid_anon_token_passes_auth_guard(client: AsyncClient, db_session):
    """A valid anon JWT must pass get_current_user_id (may still fail for other reasons)."""
    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)
    token = create_access_token(str(anon.id), is_anon=True)

    # /reflect with a valid token but non-existent submission must return 404, not 401/422
    res = await client.post(
        "/api/v1/reflect",
        json={
            "submission_id": "00000000-0000-0000-0000-000000000001",
            "response_text": "ok",
            "session_id": str(anon.id),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    # 403 (session ownership) or 404 (not found) — anything but 401 or 422
    assert res.status_code not in (401, 422), (
        f"Valid token was rejected with {res.status_code}"
    )


# ---------------------------------------------------------------------------
# Comment 1 regression: anon bootstrap → execute via cookie credential path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anon_bootstrap_sets_cookie_and_execute_succeeds(client: AsyncClient, db_session):
    """POST /auth/anon must set the debugger_session cookie so that a
    subsequent /execute call authenticated solely via that cookie succeeds
    (returns 200, not 401).  This validates the full anon bootstrap → execute
    path after the cookie-only migration."""
    from unittest.mock import patch

    # Step 1: bootstrap anon session — must set the httpOnly cookie
    anon_res = await client.post("/api/v1/auth/anon")
    assert anon_res.status_code == 201
    data = anon_res.json()
    assert "access_token" in data

    # The cookie must be present in the response
    assert "debugger_session" in anon_res.cookies, (
        "create_anon_session must set the debugger_session cookie"
    )
    cookie_token = anon_res.cookies["debugger_session"]

    # Derive session_id from the token payload (same as frontend does)
    from app.core.auth import decode_token
    payload = decode_token(cookie_token)
    session_id = payload["sub"]

    # Step 2: execute using only the cookie — no Authorization header
    mock_result = type("R", (), {
        "stdout": "1\n", "stderr": "", "traceback": "",
        "execution_time": 0.01, "success": True,
        "timed_out": False, "exit_code": 0,
    })()
    with patch("app.api.v1.routes.execute.execute_code", return_value=mock_result):
        exec_res = await client.post(
            "/api/v1/execute",
            json={"code": "print(1)", "language": "python", "session_id": session_id},
            cookies={"debugger_session": cookie_token},
        )

    assert exec_res.status_code == 200, (
        f"Expected 200 from /execute via cookie auth, got {exec_res.status_code}: "
        f"{exec_res.text}"
    )
    assert exec_res.json()["status"] == "success"
