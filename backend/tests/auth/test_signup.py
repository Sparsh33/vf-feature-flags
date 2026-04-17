"""Tests for POST /api/auth/signup."""

import pytest

from app.database.config import mongodb


@pytest.mark.asyncio
async def test_signup_happy_path(client):
    response = await client.post(
        "/api/auth/signup",
        json={"email": "alice@example.com", "password": "supersecret1", "client_name": "Acme"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["role"] == "admin"
    assert body["client"]["name"] == "Acme"
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 10
    assert len(body["api_key"]) >= 32
    database = mongodb.get_database()
    users = await database["users"].count_documents({})
    clients = await database["clients"].count_documents({})
    assert users == 1
    assert clients == 1


@pytest.mark.asyncio
async def test_signup_duplicate_email_returns_409(client):
    payload = {"email": "bob@example.com", "password": "supersecret1", "client_name": "Acme"}
    first = await client.post("/api/auth/signup", json=payload)
    assert first.status_code == 200
    second = await client.post("/api/auth/signup", json=payload)
    assert second.status_code == 409
    database = mongodb.get_database()
    clients = await database["clients"].count_documents({})
    assert clients == 1


@pytest.mark.asyncio
async def test_signup_weak_password_returns_422(client):
    response = await client.post(
        "/api/auth/signup",
        json={"email": "carol@example.com", "password": "short", "client_name": "Acme"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_invalid_email_returns_422(client):
    response = await client.post(
        "/api/auth/signup",
        json={"email": "not-an-email", "password": "supersecret1", "client_name": "Acme"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_api_key_only_returned_once(client):
    response = await client.post(
        "/api/auth/signup",
        json={"email": "dave@example.com", "password": "supersecret1", "client_name": "Acme"},
    )
    assert response.status_code == 200
    plaintext_key = response.json()["api_key"]
    database = mongodb.get_database()
    stored = await database["clients"].find_one({})
    assert stored is not None
    assert stored.get("api_key_hash") != plaintext_key
    assert plaintext_key.startswith(stored["api_key_prefix"])
