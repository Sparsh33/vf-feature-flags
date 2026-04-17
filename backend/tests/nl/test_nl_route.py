"""Endpoint tests for POST /api/nl/chat."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.nl import claude_client


@pytest.fixture
async def nl_client(monkeypatch):
    async def _fake_chat_turn(system_prompt, history, user_message):
        return ("hello there, what key?", {"flag_key": "my_flag"}, False, 10)

    monkeypatch.setattr(claude_client, "chat_turn", _fake_chat_turn)
    from app.services.nl import nl_service

    monkeypatch.setattr(nl_service.claude_client, "chat_turn", _fake_chat_turn)
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


async def test_chat_endpoint_happy_path(nl_client):
    response = await nl_client.post(
        "/api/nl/chat",
        json={"message": "make a flag"},
        headers={"X-Client-Id": "client-a", "X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert body["reply"] == "hello there, what key?"
    assert body["extracted"]["flag_key"] == "my_flag"
    assert body["compacted"] is False


async def test_chat_endpoint_requires_auth(nl_client):
    response = await nl_client.post("/api/nl/chat", json={"message": "hi"})
    assert response.status_code == 401


async def test_chat_endpoint_missing_user_id(nl_client):
    response = await nl_client.post(
        "/api/nl/chat",
        json={"message": "hi"},
        headers={"X-Client-Id": "client-a"},
    )
    assert response.status_code == 401


async def test_chat_endpoint_resumes_session(nl_client):
    first = await nl_client.post(
        "/api/nl/chat",
        json={"message": "hello"},
        headers={"X-Client-Id": "client-a", "X-User-Id": "user-1"},
    )
    session_id = first.json()["session_id"]
    second = await nl_client.post(
        "/api/nl/chat",
        json={"session_id": session_id, "message": "continue"},
        headers={"X-Client-Id": "client-a", "X-User-Id": "user-1"},
    )
    assert second.status_code == 200
    assert second.json()["session_id"] == session_id


async def test_chat_endpoint_404_unknown_session(nl_client):
    response = await nl_client.post(
        "/api/nl/chat",
        json={"session_id": "507f1f77bcf86cd799439011", "message": "hi"},
        headers={"X-Client-Id": "client-a", "X-User-Id": "user-1"},
    )
    assert response.status_code == 404
