"""Tests for POST /api/auth/login."""

import pytest


async def _signup(client, email: str = "eve@example.com", password: str = "supersecret1") -> None:
    response = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "client_name": "Acme"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_happy_path(client):
    await _signup(client)
    response = await client.post(
        "/api/auth/login",
        json={"email": "eve@example.com", "password": "supersecret1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "eve@example.com"
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 10


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    await _signup(client)
    response = await client.post(
        "/api/auth/login",
        json={"email": "eve@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(client):
    response = await client.post(
        "/api/auth/login",
        json={"email": "noone@example.com", "password": "supersecret1"},
    )
    assert response.status_code == 401
