"""Endpoint tests for POST /api/nl/chat."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.middleware.request_context import RequestContextManager
from app.services.nl import nl_route, nl_service
from app.services.nl.providers import dispatcher


async def _fake_identity() -> None:
    RequestContextManager.set_client_id("client-a")
    RequestContextManager.set_user_id("user-1")


@pytest.fixture
async def nl_client(monkeypatch):
    async def _fake_chat_turn(system_prompt, history, user_message):
        return ("hello there, what key?", {"flag_key": "my_flag"}, False, 10)

    monkeypatch.setattr(dispatcher, "chat_turn", _fake_chat_turn)
    monkeypatch.setattr(nl_service.dispatcher, "chat_turn", _fake_chat_turn)
    from main import app

    app.dependency_overrides[nl_route._resolve_identity] = _fake_identity
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    app.dependency_overrides.pop(nl_route._resolve_identity, None)


@pytest.fixture
async def unauth_nl_client(monkeypatch):
    """Client that does NOT override auth — exercises the real 401 path."""
    async def _fake_chat_turn(system_prompt, history, user_message):
        return ("hi", {}, False, 1)

    monkeypatch.setattr(dispatcher, "chat_turn", _fake_chat_turn)
    monkeypatch.setattr(nl_service.dispatcher, "chat_turn", _fake_chat_turn)
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


async def test_chat_endpoint_happy_path(nl_client):
    response = await nl_client.post("/api/nl/chat", json={"message": "make a flag"})
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert body["reply"] == "hello there, what key?"
    assert body["extracted"]["flag_key"] == "my_flag"
    assert body["compacted"] is False


async def test_chat_endpoint_requires_auth(unauth_nl_client):
    response = await unauth_nl_client.post("/api/nl/chat", json={"message": "hi"})
    assert response.status_code == 401


async def test_chat_endpoint_resumes_session(nl_client):
    first = await nl_client.post("/api/nl/chat", json={"message": "hello"})
    session_id = first.json()["session_id"]
    second = await nl_client.post(
        "/api/nl/chat",
        json={"session_id": session_id, "message": "continue"},
    )
    assert second.status_code == 200
    assert second.json()["session_id"] == session_id


async def test_chat_endpoint_404_unknown_session(nl_client):
    response = await nl_client.post(
        "/api/nl/chat",
        json={"session_id": "507f1f77bcf86cd799439011", "message": "hi"},
    )
    assert response.status_code == 404
