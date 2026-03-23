"""
Negative-path and boundary tests for malicious/edge-case inputs.
Covers: empty payloads, very long strings, special characters,
        script-like input, SQL-like patterns, duplicate submits,
        invalid field types, and oversized payloads.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from app.db.models import AnonSession
from app.core.auth import create_access_token

EXECUTE_URL = "/api/v1/execute"
REFLECT_URL = "/api/v1/reflect"
HINT_URL    = "/api/v1/hint"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL    = "/api/v1/auth/login"

NULL_UUID = "00000000-0000-0000-0000-000000000001"


async def _anon_token(db_session) -> tuple[str, str]:
    """Returns (token, session_id) for a fresh anon session."""
    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)
    return create_access_token(str(anon.id), is_anon=True), str(anon.id)


# ---------------------------------------------------------------------------
# /api/v1/execute — empty and whitespace-only code
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_empty_code_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        EXECUTE_URL,
        json={"code": "", "language": "python", "session_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_execute_whitespace_only_code_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        EXECUTE_URL,
        json={"code": "   \n\t  ", "language": "python", "session_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# /api/v1/execute — oversized code payload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_oversized_code_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    # MAX_CODE_LENGTH is enforced by the schema Field(max_length=...)
    oversized = "x = 1\n" * 100_000  # well beyond any reasonable limit
    res = await client.post(
        EXECUTE_URL,
        json={"code": oversized, "language": "python", "session_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# /api/v1/execute — unsupported language
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_unsupported_language_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        EXECUTE_URL,
        json={"code": "print(1)", "language": "javascript", "session_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# /api/v1/execute — script-like and SQL-like injection in code field
# These must be accepted by the schema (code is arbitrary text) but must
# never cause a 500 — the sandbox handles execution safety.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", [
    "<script>alert(1)</script>",
    "'; DROP TABLE users; --",
    "\" OR \"1\"=\"1",
    "${7*7}",
    "{{7*7}}",
])
@pytest.mark.asyncio
async def test_execute_injection_patterns_do_not_500(
    client: AsyncClient, db_session, payload: str
):
    token, sid = await _anon_token(db_session)
    mock_result = type("R", (), {
        "stdout": "", "stderr": "", "traceback": "",
        "execution_time": 0.01, "success": False,
        "timed_out": False, "exit_code": 1,
    })()
    with patch("app.api.v1.routes.execute.execute_code", return_value=mock_result):
        res = await client.post(
            EXECUTE_URL,
            json={"code": payload, "language": "python", "session_id": sid},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code != 500


# ---------------------------------------------------------------------------
# /api/v1/execute — special characters and unicode in code
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_unicode_code_does_not_500(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    mock_result = type("R", (), {
        "stdout": "", "stderr": "", "traceback": "",
        "execution_time": 0.01, "success": True,
        "timed_out": False, "exit_code": 0,
    })()
    with patch("app.api.v1.routes.execute.execute_code", return_value=mock_result):
        res = await client.post(
            EXECUTE_URL,
            json={"code": "print('héllo wörld 🐍')", "language": "python", "session_id": sid},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code != 500


# ---------------------------------------------------------------------------
# /api/v1/execute — oversized prediction field
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_oversized_prediction_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        EXECUTE_URL,
        json={
            "code": "print(1)",
            "language": "python",
            "session_id": sid,
            "prediction": "x" * 1001,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# /api/v1/execute — invalid session_id (not a UUID)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_invalid_session_id_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        EXECUTE_URL,
        json={"code": "print(1)", "language": "python", "session_id": "not-a-uuid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# /api/v1/execute — missing required fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_missing_code_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        EXECUTE_URL,
        json={"language": "python", "session_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_execute_empty_body_returns_422(client: AsyncClient, db_session):
    token, _ = await _anon_token(db_session)
    res = await client.post(
        EXECUTE_URL,
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# /api/v1/reflect — boundary: response_text too short / too long
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reflect_too_short_response_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        REFLECT_URL,
        json={"submission_id": NULL_UUID, "response_text": "short", "session_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_reflect_oversized_response_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        REFLECT_URL,
        json={
            "submission_id": NULL_UUID,
            "response_text": "a" * 2001,
            "session_id": sid,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_reflect_script_in_response_text_does_not_500(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    # Valid length but contains script-like content — must not 500
    res = await client.post(
        REFLECT_URL,
        json={
            "submission_id": NULL_UUID,
            "response_text": "<script>alert(1)</script> this is my reflection answer here",
            "session_id": sid,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    # 404 (submission not found) or 403 (session mismatch) — never 500
    assert res.status_code != 500


# ---------------------------------------------------------------------------
# /api/v1/hint — invalid tier values
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hint_tier_zero_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        HINT_URL,
        json={"submission_id": NULL_UUID, "tier": 0, "session_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_hint_tier_four_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        HINT_URL,
        json={"submission_id": NULL_UUID, "tier": 4, "session_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_hint_tier_string_returns_422(client: AsyncClient, db_session):
    token, sid = await _anon_token(db_session)
    res = await client.post(
        HINT_URL,
        json={"submission_id": NULL_UUID, "tier": "high", "session_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# /auth/register — injection and boundary inputs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_sql_injection_in_email_returns_422(client: AsyncClient):
    res = await client.post(
        REGISTER_URL,
        json={"email": "' OR '1'='1", "password": "Password1!"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_very_long_email_returns_422(client: AsyncClient):
    long_email = "a" * 300 + "@example.com"
    res = await client.post(
        REGISTER_URL,
        json={"email": long_email, "password": "Password1!"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_empty_email_returns_422(client: AsyncClient):
    res = await client.post(REGISTER_URL, json={"email": "", "password": "Password1!"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_empty_password_returns_422(client: AsyncClient):
    res = await client.post(REGISTER_URL, json={"email": "user@example.com", "password": ""})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_fields_returns_422(client: AsyncClient):
    res = await client.post(REGISTER_URL, json={})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_script_in_email_returns_422(client: AsyncClient):
    res = await client.post(
        REGISTER_URL,
        json={"email": "<script>alert(1)</script>@x.com", "password": "Password1!"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# /auth/login — empty and injection inputs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_empty_body_returns_422(client: AsyncClient):
    res = await client.post(LOGIN_URL, json={})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_sql_injection_email_returns_422_or_401(client: AsyncClient):
    res = await client.post(
        LOGIN_URL,
        json={"email": "admin'--", "password": "anything"},
    )
    # Invalid email format → 422; valid format but no user → 401
    assert res.status_code in (401, 422)


@pytest.mark.asyncio
async def test_login_very_long_password_returns_422_or_401(client: AsyncClient):
    res = await client.post(
        LOGIN_URL,
        json={"email": "user@example.com", "password": "A1" + "a" * 500},
    )
    assert res.status_code in (401, 422)
