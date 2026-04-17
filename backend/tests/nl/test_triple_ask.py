"""Tests for triple-ask short-circuit: 3 identical user messages sets force_action flag."""

from app.services.nl.nl_model import NLChatRequest
from app.services.nl.nl_service import chat


async def test_triple_ask_sets_force_action(mock_chat_turn):
    calls = mock_chat_turn(
        [
            ("what should the key be?", {}, False, 10),
            ("still need a key", {}, False, 10),
            ("okay, creating it with a default key", {"flag_key": "auto_key"}, False, 10),
        ]
    )
    response1 = await chat(NLChatRequest(session_id=None, message="just do it"))
    session_id = response1.session_id
    await chat(NLChatRequest(session_id=session_id, message="just do it"))
    await chat(NLChatRequest(session_id=session_id, message="just do it"))
    last_call = calls[-1]
    assert "DO NOT ASK MORE QUESTIONS" in last_call["system_prompt"]
    assert "REPEATED" in last_call["system_prompt"]


async def test_two_same_asks_no_force_action(mock_chat_turn):
    calls = mock_chat_turn(
        [
            ("ok", {}, False, 10),
            ("ok", {}, False, 10),
        ]
    )
    response1 = await chat(NLChatRequest(session_id=None, message="do it"))
    await chat(NLChatRequest(session_id=response1.session_id, message="do it"))
    for call in calls:
        assert "DO NOT ASK MORE QUESTIONS" not in call["system_prompt"]


async def test_triple_ask_case_insensitive(mock_chat_turn):
    calls = mock_chat_turn(
        [
            ("a", {}, False, 10),
            ("b", {}, False, 10),
            ("c", {}, False, 10),
        ]
    )
    response1 = await chat(NLChatRequest(session_id=None, message="Just Do It"))
    await chat(NLChatRequest(session_id=response1.session_id, message="just do it"))
    await chat(NLChatRequest(session_id=response1.session_id, message="JUST DO IT  "))
    assert "DO NOT ASK MORE QUESTIONS" in calls[-1]["system_prompt"]


async def test_different_messages_no_force_action(mock_chat_turn):
    calls = mock_chat_turn(
        [
            ("ok", {}, False, 10),
            ("ok", {}, False, 10),
            ("ok", {}, False, 10),
        ]
    )
    response1 = await chat(NLChatRequest(session_id=None, message="hello"))
    await chat(NLChatRequest(session_id=response1.session_id, message="world"))
    await chat(NLChatRequest(session_id=response1.session_id, message="foo"))
    for call in calls:
        assert "DO NOT ASK MORE QUESTIONS" not in call["system_prompt"]
