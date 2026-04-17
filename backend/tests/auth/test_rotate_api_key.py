"""Tests for POST /api/clients/rotate-api-key."""

import pytest
from fastapi import HTTPException

from app.services.auth.auth_service import AuthService
from app.services.auth.dependencies import get_current_client


async def _signup(client) -> tuple[str, str]:
    response = await client.post(
        "/api/auth/signup",
        json={"email": "helen@example.com", "password": "supersecret1", "client_name": "Acme"},
    )
    assert response.status_code == 200
    body = response.json()
    return body["access_token"], body["api_key"]


@pytest.mark.asyncio
async def test_rotate_returns_new_plaintext_key(client):
    token, original_key = await _signup(client)
    response = await client.post(
        "/api/clients/rotate-api-key", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    body = response.json()
    new_key = body["api_key"]
    assert len(new_key) >= 32
    assert new_key != original_key


@pytest.mark.asyncio
async def test_rotate_invalidates_old_key(client):
    token, original_key = await _signup(client)
    rotate_response = await client.post(
        "/api/clients/rotate-api-key", headers={"Authorization": f"Bearer {token}"}
    )
    assert rotate_response.status_code == 200
    new_key = rotate_response.json()["api_key"]
    service = AuthService()
    with pytest.raises(HTTPException) as excinfo:
        await get_current_client(x_client_api_key=original_key, service=service)
    assert excinfo.value.status_code == 401
    resolved = await get_current_client(x_client_api_key=new_key, service=service)
    assert resolved.name == "Acme"


@pytest.mark.asyncio
async def test_rotate_requires_auth(client):
    response = await client.post("/api/clients/rotate-api-key")
    assert response.status_code == 401
