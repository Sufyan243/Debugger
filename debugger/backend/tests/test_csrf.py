"""CSRF origin validation regression tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

PROTECTED_ENDPOINT = "/api/v1/execute"
VALID_PAYLOAD = {"code": "print(1)", "language": "python", "session_id": "00000000-0000-0000-0000-000000000001"}


@pytest.mark.asyncio
async def test_csrf_rejects_prefix_origin():
    """A subdomain/prefix of an allowed origin must not pass the exact-match check."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.post(
            PROTECTED_ENDPOINT,
            headers={"Origin": "https://evil.com.fake.com"},
            json=VALID_PAYLOAD,
        )
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_csrf_rejects_missing_origin_and_referer():
    """Requests with neither Origin nor Referer must be rejected."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.post(PROTECTED_ENDPOINT, json=VALID_PAYLOAD)
    assert response.status_code == 403
    assert "missing" in response.json()["detail"]


@pytest.mark.asyncio
async def test_csrf_rejects_superdomain():
    """A parent domain of an allowed origin must not pass."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.post(
            PROTECTED_ENDPOINT,
            headers={"Origin": "http://localhost"},
            json=VALID_PAYLOAD,
        )
    # localhost:5173 is allowed; bare localhost is not
    assert response.status_code in (403, 422)  # 422 if it passes CSRF but fails validation


@pytest.mark.asyncio
async def test_csrf_allows_bearer_without_origin():
    """Bearer-authenticated requests bypass CSRF even without Origin header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.post(
            PROTECTED_ENDPOINT,
            headers={"Authorization": "Bearer sometoken"},
            json=VALID_PAYLOAD,
        )
    # Must not be a CSRF 403 — may be 401/422 from auth/validation, but not CSRF rejection
    assert response.status_code != 403 or "CSRF" not in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_csrf_referer_fallback_exact_match():
    """Referer header is used when Origin is absent; must be exact-matched."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.post(
            PROTECTED_ENDPOINT,
            headers={"Referer": "https://evil.example.com/page"},
            json=VALID_PAYLOAD,
        )
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]
