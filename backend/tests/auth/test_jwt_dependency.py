"""Tests for get_current_user JWT dependency via GET /api/auth/me."""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.config.settings import settings
from app.services.auth.security import JWT_ALGORITHM


async def _signup_and_token(client) -> tuple[str, str]:
    response = await client.post(
        "/api/auth/signup",
        json={"email": "frank@example.com", "password": "supersecret1", "client_name": "Acme"},
    )
    assert response.status_code == 200
    body = response.json()
    return body["access_token"], body["user"]["id"]


@pytest.mark.asyncio
async def test_valid_token_returns_current_user(client):
    token, user_id = await _signup_and_token(client)
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user_id
    assert body["email"] == "frank@example.com"


@pytest.mark.asyncio
async def test_missing_header_returns_401(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_returns_401(client):
    response = await client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_returns_401(client):
    _, user_id = await _signup_and_token(client)
    expired_payload = {
        "sub": user_id,
        "client_id": "some-client",
        "exp": int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()),
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_non_bearer_scheme_returns_401(client):
    token, _ = await _signup_and_token(client)
    response = await client.get("/api/auth/me", headers={"Authorization": f"Basic {token}"})
    assert response.status_code == 401
