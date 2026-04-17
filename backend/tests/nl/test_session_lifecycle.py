"""Tests for session lifecycle: creation, message append, cross-client isolation."""

import pytest

from app.common.errors import NLSessionNotFound
from app.middleware.request_context import RequestContextManager
from app.services.nl.nl_model import NLChatRequest, NLMessage, NLSession
from app.services.nl.nl_service import chat
from app.services.nl.repositories.nl_repository import NLRepository


async def test_create_new_session_appends_messages(mock_chat_turn):
    mock_chat_turn([("hi, what key do you want?", {}, False, 10)])
    response = await chat(NLChatRequest(session_id=None, message="make a flag"))
    assert response.session_id
    repository = NLRepository()
    stored = await repository.get(response.session_id, "client-a")
    assert stored is not None
    assert len(stored.messages) == 2
    assert stored.messages[0].role == "user"
    assert stored.messages[0].content == "make a flag"
    assert stored.messages[1].role == "assistant"


async def test_cross_client_isolation():
    repository = NLRepository()
    session = NLSession(client_id="client-a", user_id="user-1")
    created = await repository.create(session)
    assert created.id is not None
    # client-a sees the session.
    same_client = await repository.get(created.id, "client-a")
    assert same_client is not None
    # client-b cannot see it.
    other_client = await repository.get(created.id, "client-b")
    assert other_client is None


async def test_cross_client_isolation_via_chat(mock_chat_turn):
    mock_chat_turn([("hi", {}, False, 10)])
    response = await chat(NLChatRequest(session_id=None, message="hello"))
    session_id = response.session_id
    # Switch client context; attempt to resume session as a different client.
    RequestContextManager.set_client_id("client-b")
    mock_chat_turn([("other", {}, False, 10)])
    with pytest.raises(NLSessionNotFound):
        await chat(NLChatRequest(session_id=session_id, message="try to access"))


async def test_append_message():
    repository = NLRepository()
    session = NLSession(client_id="client-a", user_id="user-1")
    created = await repository.create(session)
    assert created.id is not None
    await repository.append_message(created.id, "client-a", NLMessage(role="user", content="hello"))
    fetched = await repository.get(created.id, "client-a")
    assert fetched is not None
    assert len(fetched.messages) == 1
    assert fetched.messages[0].content == "hello"


async def test_update_patches_fields():
    repository = NLRepository()
    session = NLSession(client_id="client-a", user_id="user-1")
    created = await repository.create(session)
    assert created.id is not None
    updated = await repository.update(
        created.id, "client-a", {"status": "committed", "committed_flag_id": "flag-1"}
    )
    assert updated is not None
    assert updated.status == "committed"
    assert updated.committed_flag_id == "flag-1"


async def test_replace_messages_sets_summary_and_increments():
    repository = NLRepository()
    session = NLSession(client_id="client-a", user_id="user-1")
    created = await repository.create(session)
    assert created.id is not None
    summary_msg = NLMessage(role="assistant", content="summary turn")
    await repository.replace_messages(
        created.id, "client-a", [summary_msg], summary="a short summary"
    )
    fetched = await repository.get(created.id, "client-a")
    assert fetched is not None
    assert len(fetched.messages) == 1
    assert fetched.last_compacted_summary == "a short summary"
    assert fetched.compaction_count == 1
