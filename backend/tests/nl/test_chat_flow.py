"""Multi-turn chat flow: extract over turns, confirm, commit via flag service."""

from typing import Any, Dict, List

from app.services.nl import nl_service
from app.services.nl.nl_model import NLChatRequest


async def test_multi_turn_extract_then_commit(mock_chat_turn, monkeypatch):
    mock_chat_turn(
        [
            ("great, what cohorts?", {"flag_key": "dark_mode", "name": "Dark Mode"}, False, 10),
            (
                "so 50/50 split on true/false. Shall I save?",
                {
                    "default_value": False,
                    "cohorts": [
                        {"name": "on", "percentage": 50, "value": True},
                        {"name": "off", "percentage": 50, "value": False},
                    ],
                },
                False,
                10,
            ),
            ("saving now", {}, True, 10),
        ]
    )
    monkeypatch.setattr(
        nl_service,
        "_try_commit_flag",
        _make_commit_capture(flag_id="flag-xyz"),
    )
    response1 = await nl_service.chat(
        NLChatRequest(session_id=None, message="make a dark mode flag")
    )
    assert response1.extracted.flag_key == "dark_mode"
    assert response1.extracted.name == "Dark Mode"
    assert response1.draft_flag is None  # no cohorts yet
    assert response1.ready_to_commit is False

    response2 = await nl_service.chat(
        NLChatRequest(
            session_id=response1.session_id, message="50/50 on true and false, default false"
        )
    )
    assert response2.extracted.default_value is False
    assert response2.extracted.cohorts is not None
    assert len(response2.extracted.cohorts) == 2
    assert response2.draft_flag is not None
    assert response2.ready_to_commit is True
    assert response2.committed_flag_id is None

    response3 = await nl_service.chat(
        NLChatRequest(session_id=response1.session_id, message="yes, save it")
    )
    assert response3.committed_flag_id == "flag-xyz"


def _make_commit_capture(flag_id: str):
    async def _commit(session):
        session.status = "committed"
        session.committed_flag_id = flag_id
        return flag_id

    return _commit


async def test_confirm_without_complete_extracted_does_not_commit(mock_chat_turn, monkeypatch):
    commit_calls: List[Dict[str, Any]] = []

    async def _spy_commit(session):
        commit_calls.append({"session_id": session.id})
        return "flag-should-not-happen"

    monkeypatch.setattr(nl_service, "_try_commit_flag", _spy_commit)
    mock_chat_turn([("saving", {"flag_key": "partial"}, True, 10)])
    response = await nl_service.chat(NLChatRequest(session_id=None, message="save it please"))
    assert commit_calls == []  # skipped because extracted is incomplete
    assert response.committed_flag_id is None
    assert response.ready_to_commit is False


async def test_try_commit_flag_flagservice_missing(monkeypatch):
    """If FlagService import fails, commit returns None silently."""
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "app.services.flag.flag_service":
            raise ImportError("not available yet")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    from app.services.nl.nl_model import ExtractedParams, NLSession

    session = NLSession(
        client_id="client-a",
        user_id="user-1",
        extracted=ExtractedParams(
            flag_key="x",
            name="X",
            default_value=False,
            cohorts=[
                {"name": "on", "percentage": 50, "value": True},
                {"name": "off", "percentage": 50, "value": False},
            ],
        ),
    )
    result = await nl_service._try_commit_flag(session)
    assert result is None


async def test_draft_flag_requires_cohort_sum_100(mock_chat_turn):
    mock_chat_turn(
        [
            (
                "here are cohorts",
                {
                    "flag_key": "x",
                    "name": "X",
                    "default_value": False,
                    "cohorts": [
                        {"name": "a", "percentage": 30, "value": True},
                        {"name": "b", "percentage": 50, "value": False},
                    ],
                },
                False,
                10,
            )
        ]
    )
    response = await nl_service.chat(NLChatRequest(session_id=None, message="make it"))
    assert response.draft_flag is None
    assert response.ready_to_commit is False


async def test_triggering_compaction_sets_flag(mock_chat_turn, mock_summarize):
    mock_summarize(lambda msgs, extracted: "short summary")
    # Return token count above threshold to force compaction.
    mock_chat_turn([("reply", {"flag_key": "x"}, False, 200_000)])
    response = await nl_service.chat(NLChatRequest(session_id=None, message="hi"))
    assert response.compacted is True


class _CreatedStub:
    """Lightweight stand-in for FlagConfig returned by FlagService.create_flag."""

    id = "flag-created-123"


async def test_try_commit_flag_invokes_flag_service_with_real_request_model(monkeypatch):
    """Exercises the contract fix: `_try_commit_flag` must pass a FlagCreateRequest
    (not a raw dict) to FlagService.create_flag. Stubs `create_flag` so we can
    assert the argument type + shape, but `FlagCreateRequest(**draft)` runs for real
    and Cohort.id=None must not break validation.
    """
    from app.services.flag import flag_service as flag_service_module
    from app.services.flag.flag_model import FlagCreateRequest
    from app.services.nl.nl_model import ExtractedParams, NLSession

    captured: Dict[str, Any] = {}

    async def _fake_create_flag(self, request):
        captured["request"] = request
        return _CreatedStub()

    monkeypatch.setattr(flag_service_module.FlagService, "create_flag", _fake_create_flag)
    session = NLSession(
        client_id="client-a",
        user_id="user-1",
        extracted=ExtractedParams(
            flag_key="dark_mode",
            name="Dark Mode",
            description=None,
            default_value=False,
            cohorts=[
                # Intentionally no `id` field — covers Cohort.id=None path.
                {"name": "on", "percentage": 50, "value": True},
                {"name": "off", "percentage": 50, "value": False},
            ],
        ),
    )
    result = await nl_service._try_commit_flag(session)
    assert result == "flag-created-123"
    assert "request" in captured, "FlagService.create_flag must be called"
    request = captured["request"]
    assert isinstance(
        request, FlagCreateRequest
    ), f"create_flag must receive a FlagCreateRequest, got {type(request).__name__}"
    assert request.flag_key == "dark_mode"
    assert request.name == "Dark Mode"
    assert request.default_value is False
    assert len(request.cohorts) == 2
    assert all(cohort.id is None for cohort in request.cohorts)


async def test_try_commit_flag_invalid_draft_returns_none(monkeypatch):
    """If `FlagCreateRequest(**draft)` fails validation, commit returns None and
    does not blow up the caller. No FlagService.create_flag call is made.
    """
    from unittest.mock import AsyncMock
    from app.services.flag import flag_service as flag_service_module
    from app.services.nl.nl_model import ExtractedParams, NLSession

    create_flag_mock = AsyncMock()
    monkeypatch.setattr(flag_service_module.FlagService, "create_flag", create_flag_mock)
    session = NLSession(
        client_id="client-a",
        user_id="user-1",
        extracted=ExtractedParams(
            flag_key="x",
            name="X",
            default_value=False,
            cohorts=[
                {"name": "on", "percentage": 50, "value": True},
                {"name": "off", "percentage": 50, "value": False},
            ],
        ),
    )

    def _bad_draft(_extracted):
        return {"flag_key": 123, "name": None}  # wrong types: FlagCreateRequest rejects

    monkeypatch.setattr(nl_service, "_build_draft_flag", _bad_draft)
    result = await nl_service._try_commit_flag(session)
    assert result is None
    create_flag_mock.assert_not_called()
