"""Tests for the get_current_client dependency (X-Client-API-Key)."""

import pytest
from fastapi import HTTPException

from app.services.auth.auth_service import AuthService
from app.services.auth.dependencies import get_current_client


async def _signup_get_key(client) -> str:
    response = await client.post(
        "/api/auth/signup",
        json={"email": "gina@example.com", "password": "supersecret1", "client_name": "Acme"},
    )
    assert response.status_code == 200
    return response.json()["api_key"]


@pytest.mark.asyncio
async def test_valid_api_key_returns_client(client):
    plaintext_key = await _signup_get_key(client)
    service = AuthService()
    result = await get_current_client(x_client_api_key=plaintext_key, service=service)
    assert result.name == "Acme"
    assert result.id


@pytest.mark.asyncio
async def test_missing_header_raises_401(client):
    service = AuthService()
    with pytest.raises(HTTPException) as excinfo:
        await get_current_client(x_client_api_key=None, service=service)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_key_raises_401(client):
    await _signup_get_key(client)
    service = AuthService()
    with pytest.raises(HTTPException) as excinfo:
        await get_current_client(x_client_api_key="totally-bogus-key-123456789", service=service)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_correct_prefix_wrong_full_value_raises_401(client):
    plaintext_key = await _signup_get_key(client)
    prefix = plaintext_key[:8]
    forged_key = prefix + "X" * 32
    service = AuthService()
    with pytest.raises(HTTPException) as excinfo:
        await get_current_client(x_client_api_key=forged_key, service=service)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_short_key_raises_401(client):
    service = AuthService()
    with pytest.raises(HTTPException) as excinfo:
        await get_current_client(x_client_api_key="short", service=service)
    assert excinfo.value.status_code == 401
