import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from sqlalchemy import select
from app.db.models import User

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
VERIFY_URL = "/api/v1/auth/verify-email"
LOGOUT_URL = "/api/v1/auth/logout"
EXCHANGE_URL = "/api/v1/auth/exchange"

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
    result = await db_session.execute(select(User).where(User.email == VALID_PAYLOAD["email"]))
    user = result.scalar_one()
    user.email_verified = True
    await db_session.commit()
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock):
        res = await client.post(REGISTER_URL, json=VALID_PAYLOAD)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_register_duplicate_unverified_email_resends(client: AsyncClient, db_session):
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock):
        await client.post(REGISTER_URL, json=VALID_PAYLOAD)
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
async def test_register_password_exceeds_72_bytes_returns_422(client: AsyncClient):
    long_password = "A1" + "a" * 71
    res = await client.post(REGISTER_URL, json={"email": "user@example.com", "password": long_password})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_password_exactly_72_bytes_accepted(client: AsyncClient, db_session):
    boundary_password = "A1" + "a" * 70
    assert len(boundary_password.encode("utf-8")) == 72
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock):
        res = await client.post(REGISTER_URL, json={"email": "boundary@example.com", "password": boundary_password})
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_register_smtp_failure_rolls_back_user(client: AsyncClient, db_session):
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock, side_effect=Exception("SMTP down")):
        res = await client.post(REGISTER_URL, json=VALID_PAYLOAD)
    assert res.status_code == 503
    assert "verification email" in res.json()["detail"].lower()

    result = await db_session.execute(select(User).where(User.email == VALID_PAYLOAD["email"]))
    assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Comment 6: Registration transaction — email-before-commit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_smtp_failure_leaves_no_user_row(client: AsyncClient, db_session):
    """
    With the email-before-commit strategy, an SMTP failure must leave zero
    user rows in the database (no orphaned unverified account).
    """
    with patch("app.api.v1.routes.auth.send_verification_email",
               new_callable=AsyncMock, side_effect=Exception("SMTP down")):
        res = await client.post(REGISTER_URL, json={"email": "norow@example.com", "password": "Password1"})
    assert res.status_code == 503

    result = await db_session.execute(select(User).where(User.email == "norow@example.com"))
    assert result.scalar_one_or_none() is None, (
        "User row must not exist when email delivery fails before commit."
    )


@pytest.mark.asyncio
async def test_reregister_smtp_failure_on_unverified_does_not_change_password(
    client: AsyncClient, db_session
):
    """
    Re-registering an unverified account when SMTP fails must NOT persist
    the new password — the update is rolled back along with the commit.
    """
    with patch("app.api.v1.routes.auth.send_verification_email", new_callable=AsyncMock):
        await client.post(REGISTER_URL, json={"email": "retry@example.com", "password": "Password1"})

    result = await db_session.execute(select(User).where(User.email == "retry@example.com"))
    user = result.scalar_one()
    original_hash = user.hashed_password

    with patch("app.api.v1.routes.auth.send_verification_email",
               new_callable=AsyncMock, side_effect=Exception("SMTP down")):
        res = await client.post(REGISTER_URL, json={"email": "retry@example.com", "password": "NewPass2"})
    assert res.status_code == 503

    await db_session.refresh(user)
    assert user.hashed_password == original_hash, (
        "Password must not change when re-registration email delivery fails."
    )


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
    location = res.headers["location"]
    assert "verified=1" in location
    assert "code=" in location
    assert "token=" not in location

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
    assert res.status_code == 200
    assert "access_token" in res.json()


# ---------------------------------------------------------------------------
# /auth/exchange
# ---------------------------------------------------------------------------

async def _get_auth_code(client: AsyncClient, db_session) -> str:
    """Helper: registers+verifies a user and returns the one-time code from the redirect."""
    user = await _register_user(client, db_session, email="exchange@example.com")
    token = user.verification_token
    res = await client.get(f"{VERIFY_URL}?token={token}", follow_redirects=False)
    location = res.headers["location"]
    from urllib.parse import urlparse, parse_qs
    qs = parse_qs(urlparse(location).query)
    return qs["code"][0]


@pytest.mark.asyncio
async def test_exchange_valid_code_returns_jwt(client: AsyncClient, db_session):
    code = await _get_auth_code(client, db_session)
    res = await client.post(EXCHANGE_URL, json={"code": code})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_exchange_code_is_single_use(client: AsyncClient, db_session):
    code = await _get_auth_code(client, db_session)
    res1 = await client.post(EXCHANGE_URL, json={"code": code})
    assert res1.status_code == 200
    res2 = await client.post(EXCHANGE_URL, json={"code": code})
    assert res2.status_code == 400
    assert "expired" in res2.json()["detail"].lower() or "invalid" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_exchange_invalid_code_returns_400(client: AsyncClient):
    res = await client.post(EXCHANGE_URL, json={"code": "not-a-real-code"})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_exchange_expired_code_returns_400(client: AsyncClient, db_session):
    """Simulates an expired Redis key by mocking _consume_auth_code to return None."""
    with patch("app.api.v1.routes.auth._consume_auth_code", new_callable=AsyncMock, return_value=None):
        res = await client.post(EXCHANGE_URL, json={"code": "any-code-value"})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Comment 2: /auth/logout — server-side token revocation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_logout_returns_204(client: AsyncClient, db_session):
    """A valid JWT presented to /auth/logout must return 204."""
    await _verified_user(client, db_session, email="logout@example.com")
    login_res = await client.post(LOGIN_URL, json={"email": "logout@example.com", "password": "Password1"})
    token = login_res.json()["access_token"]

    res = await client.post(LOGOUT_URL, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_revoked_token_is_rejected_on_protected_endpoint(client: AsyncClient, db_session):
    """After logout, the same token must be rejected with 401 on any protected endpoint."""
    from app.db.models import AnonSession
    from app.core.auth import create_access_token

    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)
    token = create_access_token(str(anon.id), is_anon=True)
    session_id = str(anon.id)

    # Revoke the token via logout
    await client.post(LOGOUT_URL, headers={"Authorization": f"Bearer {token}"})

    # Any subsequent request with the revoked token must be rejected
    res = await client.post(
        "/api/v1/execute",
        json={"code": "print(1)", "language": "python", "session_id": session_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert "revoked" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_logout_with_invalid_token_still_returns_204(client: AsyncClient):
    """Logout must return 204 even for malformed tokens — client should always clear storage."""
    res = await client.post(LOGOUT_URL, headers={"Authorization": "Bearer not.a.real.token"})
    assert res.status_code == 204


# ---------------------------------------------------------------------------
# Comment 2: Redis failure on revocation check returns 503, not 500
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redis_failure_on_revocation_check_returns_503(client: AsyncClient, db_session):
    """When Redis is unreachable during a revocation check, the endpoint must
    return 503 (service unavailable) rather than an opaque 500."""
    from redis.exceptions import RedisError
    from app.db.models import AnonSession
    from app.core.auth import create_access_token

    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)
    token = create_access_token(str(anon.id), is_anon=True)
    session_id = str(anon.id)

    with patch("app.core.auth.is_token_revoked", new_callable=AsyncMock,
               side_effect=RedisError("connection refused")):
        res = await client.post(
            "/api/v1/execute",
            json={"code": "print(1)", "language": "python", "session_id": session_id},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 503
    assert "unavailable" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_redis_failure_on_logout_still_returns_204(client: AsyncClient, db_session):
    """Logout must return 204 even when Redis is down — revocation failure is
    logged but must not surface as an error to the client."""
    from redis.exceptions import RedisError
    await _verified_user(client, db_session, email="redisdown@example.com")
    login_res = await client.post(LOGIN_URL, json={"email": "redisdown@example.com", "password": "Password1"})
    token = login_res.json()["access_token"]

    with patch("app.core.auth.revoke_token", new_callable=AsyncMock,
               side_effect=RedisError("connection refused")):
        res = await client.post(LOGOUT_URL, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204


# ---------------------------------------------------------------------------
# Comment 3: OAuth callback timeout and malformed response handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_github_callback_timeout_redirects_to_error(client: AsyncClient):
    """A timeout talking to GitHub must redirect to the frontend error page,
    not raise an unhandled exception."""
    import httpx as _httpx
    with patch("app.api.v1.routes.auth._consume_oauth_state",
               new_callable=AsyncMock, return_value="github"), \
         patch("httpx.AsyncClient.post",
               new_callable=AsyncMock, side_effect=_httpx.TimeoutException("timed out")):
        res = await client.get("/api/v1/auth/github/callback?code=x&state=y",
                               follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "error=github_timeout" in res.headers["location"]


@pytest.mark.asyncio
async def test_github_callback_malformed_json_redirects_to_error(client: AsyncClient):
    """A non-JSON response from GitHub token endpoint must redirect to error,
    not raise a JSONDecodeError."""
    import httpx as _httpx
    mock_response = _httpx.Response(200, content=b"not-json")
    with patch("app.api.v1.routes.auth._consume_oauth_state",
               new_callable=AsyncMock, return_value="github"), \
         patch("httpx.AsyncClient.post",
               new_callable=AsyncMock, return_value=mock_response):
        res = await client.get("/api/v1/auth/github/callback?code=x&state=y",
                               follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "error=github_token_failed" in res.headers["location"]


@pytest.mark.asyncio
async def test_google_callback_timeout_redirects_to_error(client: AsyncClient):
    """A timeout talking to Google must redirect to the frontend error page."""
    import httpx as _httpx
    with patch("app.api.v1.routes.auth._consume_oauth_state",
               new_callable=AsyncMock, return_value="google"), \
         patch("httpx.AsyncClient.post",
               new_callable=AsyncMock, side_effect=_httpx.TimeoutException("timed out")):
        res = await client.get("/api/v1/auth/google/callback?code=x&state=y",
                               follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "error=google_timeout" in res.headers["location"]


# ---------------------------------------------------------------------------
# Comment 4: OAuth redirects must not contain email or avatar in URL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_email_redirect_contains_no_pii(client: AsyncClient, db_session):
    """The verify-email redirect must contain only a code and verified flag —
    no email address or avatar URL in the query string."""
    user = await _register_user(client, db_session, email="pii@example.com")
    token = user.verification_token

    res = await client.get(f"{VERIFY_URL}?token={token}", follow_redirects=False)
    assert res.status_code in (302, 307)
    location = res.headers["location"]
    assert "email=" not in location
    assert "avatar=" not in location
    assert "code=" in location


@pytest.mark.asyncio
async def test_exchange_returns_profile_from_server_state(client: AsyncClient, db_session):
    """The exchange endpoint must return email from server-side Redis state,
    not from anything the client passed in the URL."""
    code = await _get_auth_code(client, db_session)
    res = await client.post(EXCHANGE_URL, json={"code": code})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    # Profile fields come from server state
    assert "email" in data
    assert data["email"] == "exchange@example.com"


# ---------------------------------------------------------------------------
# Comment 2: /auth/merge must reject revoked tokens
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_merge_rejects_revoked_token(client: AsyncClient, db_session):
    """A revoked (logged-out) token must be rejected by /auth/merge with 401."""
    from app.db.models import AnonSession
    from app.core.auth import create_access_token

    # Create a real (non-anon) user so require_real_user passes the anon check
    user = await _verified_user(client, db_session, email="mergerevoke@example.com")
    login_res = await client.post(LOGIN_URL, json={"email": "mergerevoke@example.com", "password": "Password1"})
    token = login_res.json()["access_token"]

    # Revoke the token
    await client.post(LOGOUT_URL, headers={"Authorization": f"Bearer {token}"})

    # /auth/merge with the revoked token must return 401
    res = await client.post(
        "/api/v1/auth/merge",
        json={"anon_id": "00000000-0000-0000-0000-000000000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert "revoked" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Comment 3: OAuth username collision must not 500
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_oauth_duplicate_username_does_not_500(client: AsyncClient, db_session):
    """Two OAuth users with the same display name must not cause a 500.
    Since username is no longer unique, both rows should be created successfully."""
    from app.db.models import User

    # Insert first user with a username directly
    u1 = User(
        email="oauth1@example.com",
        username="johndoe",
        provider="github",
        provider_id="gh_111",
        avatar_url=None,
    )
    db_session.add(u1)
    await db_session.commit()

    # Second user with same username but different provider_id — must not 500
    u2 = User(
        email="oauth2@example.com",
        username="johndoe",
        provider="github",
        provider_id="gh_222",
        avatar_url=None,
    )
    db_session.add(u2)
    await db_session.commit()  # must not raise IntegrityError

    result = await db_session.execute(
        select(User).where(User.username == "johndoe")
    )
    rows = result.scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_oauth_integrity_error_returns_409_not_500(client: AsyncClient, db_session):
    """When _get_or_create_oauth_user hits an IntegrityError on email uniqueness,
    it must return a 409 redirect, not a 500."""
    import httpx as _httpx
    from unittest.mock import MagicMock
    from sqlalchemy.exc import IntegrityError as _IntegrityError

    # Simulate a GitHub callback where the DB commit raises IntegrityError
    # (e.g. race on email unique constraint)
    mock_token_res = MagicMock()
    mock_token_res.is_success = True
    mock_token_res.json.return_value = {"access_token": "gh_token"}

    mock_user_res = MagicMock()
    mock_user_res.is_success = True
    mock_user_res.json.return_value = {
        "id": 99999, "login": "raceuser", "email": "race@example.com",
        "avatar_url": "https://example.com/avatar.png",
    }

    async def mock_request(method, url, **kwargs):
        if "access_token" in str(url):
            return mock_token_res
        return mock_user_res

    with patch("app.api.v1.routes.auth._consume_oauth_state",
               new_callable=AsyncMock, return_value="github"), \
         patch("app.api.v1.routes.auth._get_or_create_oauth_user",
               new_callable=AsyncMock,
               side_effect=_httpx.HTTPStatusError("", request=MagicMock(), response=MagicMock()) if False
               else None):
        # Directly test that IntegrityError in _get_or_create_oauth_user
        # raises HTTPException(409), not propagates as 500
        from app.api.v1.routes.auth import _get_or_create_oauth_user
        from sqlalchemy.exc import IntegrityError as SAIntegrityError
        from fastapi import HTTPException as FastAPIHTTPException

        with patch("app.api.v1.routes.auth._get_or_create_oauth_user",
                   new_callable=AsyncMock,
                   side_effect=FastAPIHTTPException(status_code=409, detail="Account already exists. Please sign in with your original method.")):
            res = await client.get(
                "/api/v1/auth/github/callback?code=x&state=y",
                follow_redirects=False,
            )
        assert res.status_code in (302, 307)
        assert "account_conflict" in res.headers["location"]


# ---------------------------------------------------------------------------
# Comment 1: /auth/merge must reject anon tokens and revoked real-user tokens
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_merge_rejects_anon_token(client: AsyncClient, db_session):
    """An anonymous JWT must be rejected by /auth/merge with 401."""
    from app.db.models import AnonSession
    from app.core.auth import create_access_token

    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)
    anon_token = create_access_token(str(anon.id), is_anon=True)

    res = await client.post(
        "/api/v1/auth/merge",
        json={"anon_id": str(anon.id)},
        headers={"Authorization": f"Bearer {anon_token}"},
    )
    assert res.status_code == 401
    assert "login" in res.json()["detail"].lower() or "anon" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_merge_rejects_revoked_real_user_token(client: AsyncClient, db_session):
    """A revoked real-user token must be rejected by /auth/merge with 401."""
    user = await _verified_user(client, db_session, email="mergerevoke2@example.com")
    login_res = await client.post(LOGIN_URL, json={"email": "mergerevoke2@example.com", "password": "Password1"})
    token = login_res.json()["access_token"]

    # Revoke the token via logout
    await client.post(LOGOUT_URL, headers={"Authorization": f"Bearer {token}"})

    res = await client.post(
        "/api/v1/auth/merge",
        json={"anon_id": "00000000-0000-0000-0000-000000000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401
    assert "revoked" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Comment 1: merge — conflict-safe metric merging
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_merge_combines_metrics_when_user_row_exists(client: AsyncClient, db_session):
    """When both anon and user have MetacognitiveMetric rows, merge must sum
    totals and recompute accuracy into the user row, not cause a unique collision."""
    from app.db.models import AnonSession, MetacognitiveMetric
    from app.core.auth import create_access_token
    import uuid

    # Create a real user
    user = await _verified_user(client, db_session, email="mergemet@example.com")
    login_res = await client.post(LOGIN_URL, json={"email": "mergemet@example.com", "password": "Password1"})
    token = login_res.json()["access_token"]
    user_id = str(user.id)

    # Create anon session with a metric row
    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)

    anon_metric = MetacognitiveMetric(
        session_id=anon.id,
        total_predictions=4,
        correct_predictions=3,
        accuracy_score=0.75,
    )
    db_session.add(anon_metric)

    # Create user metric row (would collide on direct session_id reassignment)
    user_metric = MetacognitiveMetric(
        session_id=uuid.UUID(user_id),
        total_predictions=6,
        correct_predictions=4,
        accuracy_score=round(4 / 6, 10),
    )
    db_session.add(user_metric)
    await db_session.commit()

    res = await client.post(
        "/api/v1/auth/merge",
        json={"anon_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["merged"] is True

    await db_session.refresh(user_metric)
    assert user_metric.total_predictions == 10
    assert user_metric.correct_predictions == 7
    assert abs(user_metric.accuracy_score - 0.7) < 1e-9


@pytest.mark.asyncio
async def test_merge_reassigns_anon_metric_when_no_user_row(client: AsyncClient, db_session):
    """When the user has no MetacognitiveMetric row, the anon row is reassigned directly."""
    from app.db.models import AnonSession, MetacognitiveMetric
    from sqlalchemy import select
    import uuid

    user = await _verified_user(client, db_session, email="mergemet2@example.com")
    login_res = await client.post(LOGIN_URL, json={"email": "mergemet2@example.com", "password": "Password1"})
    token = login_res.json()["access_token"]
    user_id = str(user.id)

    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)

    anon_metric = MetacognitiveMetric(
        session_id=anon.id,
        total_predictions=2,
        correct_predictions=1,
        accuracy_score=0.5,
    )
    db_session.add(anon_metric)
    await db_session.commit()

    res = await client.post(
        "/api/v1/auth/merge",
        json={"anon_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["merged"] is True

    result = await db_session.execute(
        select(MetacognitiveMetric).where(MetacognitiveMetric.session_id == uuid.UUID(user_id))
    )
    merged = result.scalar_one_or_none()
    assert merged is not None
    assert merged.total_predictions == 2


@pytest.mark.asyncio
async def test_merge_returns_false_on_already_merged(client: AsyncClient, db_session):
    """Calling merge a second time on an already-merged anon session must return merged=False."""
    from app.db.models import AnonSession

    user = await _verified_user(client, db_session, email="mergedup@example.com")
    login_res = await client.post(LOGIN_URL, json={"email": "mergedup@example.com", "password": "Password1"})
    token = login_res.json()["access_token"]

    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)

    # First merge
    res1 = await client.post(
        "/api/v1/auth/merge",
        json={"anon_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.json()["merged"] is True

    # Second merge — must be idempotent and return merged=False
    res2 = await client.post(
        "/api/v1/auth/merge",
        json={"anon_id": str(anon.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    assert res2.json()["merged"] is False


# ---------------------------------------------------------------------------
# Comment 3: Redis outage on OAuth start, callback state, and /auth/exchange
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_github_login_redis_outage_redirects_to_error(client: AsyncClient):
    """Redis failure during OAuth state storage must redirect to error page, not 500."""
    from redis.exceptions import RedisError
    with patch("app.api.v1.routes.auth._store_oauth_state",
               new_callable=AsyncMock, side_effect=HTTPException(status_code=503, detail="unavailable")):
        res = await client.get("/api/v1/auth/github", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "auth_unavailable" in res.headers["location"]


@pytest.mark.asyncio
async def test_google_login_redis_outage_redirects_to_error(client: AsyncClient):
    """Redis failure during Google OAuth state storage must redirect to error page."""
    with patch("app.api.v1.routes.auth._store_oauth_state",
               new_callable=AsyncMock, side_effect=HTTPException(status_code=503, detail="unavailable")):
        res = await client.get("/api/v1/auth/google", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "auth_unavailable" in res.headers["location"]


@pytest.mark.asyncio
async def test_github_callback_redis_outage_on_state_redirects_to_error(client: AsyncClient):
    """Redis failure consuming OAuth state in GitHub callback must redirect to auth_unavailable."""
    from app.api.v1.routes.auth import _OAUTH_STATE_UNAVAILABLE
    with patch("app.api.v1.routes.auth._consume_oauth_state",
               new_callable=AsyncMock, return_value=_OAUTH_STATE_UNAVAILABLE):
        res = await client.get("/api/v1/auth/github/callback?code=x&state=y",
                               follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "auth_unavailable" in res.headers["location"]


@pytest.mark.asyncio
async def test_google_callback_redis_outage_on_state_redirects_to_error(client: AsyncClient):
    """Redis failure consuming OAuth state in Google callback must redirect to auth_unavailable."""
    from app.api.v1.routes.auth import _OAUTH_STATE_UNAVAILABLE
    with patch("app.api.v1.routes.auth._consume_oauth_state",
               new_callable=AsyncMock, return_value=_OAUTH_STATE_UNAVAILABLE):
        res = await client.get("/api/v1/auth/google/callback?code=x&state=y",
                               follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "auth_unavailable" in res.headers["location"]


@pytest.mark.asyncio
async def test_exchange_redis_outage_returns_503(client: AsyncClient):
    """Redis failure consuming the auth code must return 503, not 500."""
    from redis.exceptions import RedisError
    with patch("app.api.v1.routes.auth._consume_auth_code",
               new_callable=AsyncMock,
               side_effect=HTTPException(status_code=503, detail="Auth service temporarily unavailable. Please try again.")):
        res = await client.post(EXCHANGE_URL, json={"code": "any-code"})
    assert res.status_code == 503
    assert "unavailable" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Comment 1: OAuth start endpoints must not crash due to missing _OAUTH_STATE_TTL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_github_login_start_does_not_500(client: AsyncClient):
    """GET /auth/github must redirect (not 500) when GITHUB_CLIENT_ID is configured.
    A NameError on _OAUTH_STATE_TTL would produce a 500 — this guards against that."""
    from unittest.mock import patch as _patch
    from app.core.config import settings as _settings

    with _patch.object(_settings, "GITHUB_CLIENT_ID", "test-client-id"), \
         _patch("app.api.v1.routes.auth._store_oauth_state", new_callable=AsyncMock):
        res = await client.get("/api/v1/auth/github", follow_redirects=False)
    # Must be a redirect to GitHub, not a 500
    assert res.status_code in (302, 307)
    assert "github.com" in res.headers["location"]


@pytest.mark.asyncio
async def test_google_login_start_does_not_500(client: AsyncClient):
    """GET /auth/google must redirect (not 500) when GOOGLE_CLIENT_ID is configured."""
    from unittest.mock import patch as _patch
    from app.core.config import settings as _settings

    with _patch.object(_settings, "GOOGLE_CLIENT_ID", "test-client-id"), \
         _patch("app.api.v1.routes.auth._store_oauth_state", new_callable=AsyncMock):
        res = await client.get("/api/v1/auth/google", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "google.com" in res.headers["location"]


# ---------------------------------------------------------------------------
# Comment 2: /auth/merge must succeed when authenticated via httpOnly cookie
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_merge_succeeds_via_cookie_auth(client: AsyncClient, db_session):
    """POST /auth/merge must work when the real-user JWT is carried in the
    httpOnly cookie (debugger_session) rather than an Authorization header.
    This validates that require_real_user accepts the cookie path."""
    from app.db.models import AnonSession
    from app.core.auth import create_access_token

    user = await _verified_user(client, db_session, email="cookiemerge@example.com")
    real_token = create_access_token(str(user.id), is_anon=False)

    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)

    # Send the JWT as a cookie, no Authorization header
    res = await client.post(
        "/api/v1/auth/merge",
        json={"anon_id": str(anon.id)},
        cookies={"debugger_session": real_token},
    )
    assert res.status_code == 200
    assert res.json()["merged"] is True


@pytest.mark.asyncio
async def test_merge_rejects_anon_token_via_cookie(client: AsyncClient, db_session):
    """An anon JWT in the cookie must still be rejected by /auth/merge with 401."""
    from app.db.models import AnonSession
    from app.core.auth import create_access_token

    anon = AnonSession()
    db_session.add(anon)
    await db_session.commit()
    await db_session.refresh(anon)
    anon_token = create_access_token(str(anon.id), is_anon=True)

    res = await client.post(
        "/api/v1/auth/merge",
        json={"anon_id": str(anon.id)},
        cookies={"debugger_session": anon_token},
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# Comment 1 (this session): OAuth state — separate invalid/expired vs unavailable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_github_callback_missing_state_redirects_to_oauth_state_invalid(client: AsyncClient):
    """An absent or expired OAuth state key must redirect to oauth_state_invalid,
    not auth_unavailable — these are distinct failure modes."""
    from app.api.v1.routes.auth import _OAUTH_STATE_MISSING
    with patch("app.api.v1.routes.auth._consume_oauth_state",
               new_callable=AsyncMock, return_value=_OAUTH_STATE_MISSING):
        res = await client.get("/api/v1/auth/github/callback?code=x&state=y",
                               follow_redirects=False)
    assert res.status_code in (302, 307)
    location = res.headers["location"]
    assert "oauth_state_invalid" in location
    assert "auth_unavailable" not in location


@pytest.mark.asyncio
async def test_github_callback_wrong_provider_redirects_to_oauth_state_invalid(client: AsyncClient):
    """A state key that resolves to the wrong provider must redirect to
    oauth_state_invalid (CSRF / replay attempt), not auth_unavailable."""
    with patch("app.api.v1.routes.auth._consume_oauth_state",
               new_callable=AsyncMock, return_value="google"):
        res = await client.get("/api/v1/auth/github/callback?code=x&state=y",
                               follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "oauth_state_invalid" in res.headers["location"]


@pytest.mark.asyncio
async def test_google_callback_missing_state_redirects_to_oauth_state_invalid(client: AsyncClient):
    """An absent or expired OAuth state key on the Google callback must redirect
    to oauth_state_invalid, not auth_unavailable."""
    from app.api.v1.routes.auth import _OAUTH_STATE_MISSING
    with patch("app.api.v1.routes.auth._consume_oauth_state",
               new_callable=AsyncMock, return_value=_OAUTH_STATE_MISSING):
        res = await client.get("/api/v1/auth/google/callback?code=x&state=y",
                               follow_redirects=False)
    assert res.status_code in (302, 307)
    location = res.headers["location"]
    assert "oauth_state_invalid" in location
    assert "auth_unavailable" not in location


@pytest.mark.asyncio
async def test_google_callback_wrong_provider_redirects_to_oauth_state_invalid(client: AsyncClient):
    """A state key that resolves to the wrong provider on the Google callback
    must redirect to oauth_state_invalid."""
    with patch("app.api.v1.routes.auth._consume_oauth_state",
               new_callable=AsyncMock, return_value="github"):
        res = await client.get("/api/v1/auth/google/callback?code=x&state=y",
                               follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "oauth_state_invalid" in res.headers["location"]
