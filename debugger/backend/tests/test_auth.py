import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy import select
from app.db.models import User

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
VERIFY_URL = "/api/v1/auth/verify-email"

VALID_PAYLOAD = {"email": "user@example.com", "password": "Password1"}


# ---------------------------------------------------------------------------
# /auth/register
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_sends_email_and_returns_201(client: AsyncClient, db_session):
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock) as mock_send:
        res = await client.post(REGISTER_URL, json=VALID_PAYLOAD)
    assert res.status_code == 201
    assert "Verification email sent" in res.json()["detail"]
    mock_send.assert_awaited_once()

    result = await db_session.execute(select(User).where(User.email == VALID_PAYLOAD["email"]))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email_verified is False
    assert user.verification_token is not None
    assert user.verification_token_expires_at is not None


@pytest.mark.asyncio
async def test_register_duplicate_verified_email_returns_409(client: AsyncClient, db_session):
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock):
        await client.post(REGISTER_URL, json=VALID_PAYLOAD)
    # Manually verify the user
    result = await db_session.execute(select(User).where(User.email == VALID_PAYLOAD["email"]))
    user = result.scalar_one()
    user.email_verified = True
    await db_session.commit()
    # Now re-registering the same verified email must return 409
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock):
        res = await client.post(REGISTER_URL, json=VALID_PAYLOAD)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_register_duplicate_unverified_email_resends(client: AsyncClient, db_session):
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock):
        await client.post(REGISTER_URL, json=VALID_PAYLOAD)
    # Re-registering an unverified account resends and returns 201
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock) as mock_resend:
        res = await client.post(REGISTER_URL, json=VALID_PAYLOAD)
    assert res.status_code == 201
    mock_resend.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_weak_password_returns_422(client: AsyncClient):
    res = await client.post(REGISTER_URL, json={"email": "user@example.com", "password": "short"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_password_no_digit_returns_422(client: AsyncClient):
    res = await client.post(REGISTER_URL, json={"email": "user@example.com", "password": "NoDigitPass"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_smtp_failure_rolls_back_user(client: AsyncClient, db_session):
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock, side_effect=Exception("SMTP down")):
        res = await client.post(REGISTER_URL, json=VALID_PAYLOAD)
    assert res.status_code == 503
    assert "verification email" in res.json()["detail"].lower()

    result = await db_session.execute(select(User).where(User.email == VALID_PAYLOAD["email"]))
    assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# /auth/verify-email
# ---------------------------------------------------------------------------

async def _register_user(client, db_session, email="user@example.com"):
    """Helper: registers a user and returns the raw User row."""
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock):
        await client.post(REGISTER_URL, json={"email": email, "password": "Password1"})
    result = await db_session.execute(select(User).where(User.email == email))
    return result.scalar_one()


@pytest.mark.asyncio
async def test_verify_email_valid_token_sets_verified_and_redirects(client: AsyncClient, db_session):
    user = await _register_user(client, db_session)
    token = user.verification_token

    res = await client.get(f"{VERIFY_URL}?token={token}", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "verified=1" in res.headers["location"]
    assert "token=" in res.headers["location"]

    await db_session.refresh(user)
    assert user.email_verified is True
    assert user.verification_token is None
    assert user.verification_token_expires_at is None


@pytest.mark.asyncio
async def test_verify_email_invalid_token_redirects_to_error(client: AsyncClient):
    res = await client.get(f"{VERIFY_URL}?token=invalid-token-xyz", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "verified=error" in res.headers["location"]


@pytest.mark.asyncio
async def test_verify_email_expired_token_redirects_to_expired(client: AsyncClient, db_session):
    user = await _register_user(client, db_session)
    # Force expiry into the past
    user.verification_token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()
    token = user.verification_token

    res = await client.get(f"{VERIFY_URL}?token={token}", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "verified=expired" in res.headers["location"]

    await db_session.refresh(user)
    assert user.email_verified is False
    assert user.verification_token is None


# ---------------------------------------------------------------------------
# /auth/login
# ---------------------------------------------------------------------------

async def _verified_user(client, db_session, email="verified@example.com"):
    """Helper: registers and manually verifies a user."""
    user = await _register_user(client, db_session, email=email)
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_login_verified_user_returns_token(client: AsyncClient, db_session):
    await _verified_user(client, db_session)
    res = await client.post(LOGIN_URL, json={"email": "verified@example.com", "password": "Password1"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_unverified_user_returns_403(client: AsyncClient, db_session):
    await _register_user(client, db_session, email="unverified@example.com")
    res = await client.post(LOGIN_URL, json={"email": "unverified@example.com", "password": "Password1"})
    assert res.status_code == 403
    assert "not verified" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient, db_session):
    await _verified_user(client, db_session)
    res = await client.post(LOGIN_URL, json={"email": "verified@example.com", "password": "WrongPass9"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client: AsyncClient):
    res = await client.post(LOGIN_URL, json={"email": "ghost@example.com", "password": "Password1"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_no_complexity_check_on_existing_weak_password(client: AsyncClient, db_session):
    """Login must not reject requests based on password complexity rules."""
    from app.core.auth import hash_password
    user = User(
        email="legacy@example.com",
        hashed_password=hash_password("weak"),
        provider="email",
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()

    res = await client.post(LOGIN_URL, json={"email": "legacy@example.com", "password": "weak"})
    # Correct password + verified account — must succeed regardless of complexity
    assert res.status_code == 200
    assert "access_token" in res.json()
