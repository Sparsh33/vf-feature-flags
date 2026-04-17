"""Natural-language flag builder service.

Orchestrates the chat turn: session load/create, system prompt assembly, Claude
invocation, draft merging, compaction, and optional flag commit.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from app.common.errors import NLSessionNotFound
from app.common.logging_helpers import LoggingData, log_error, log_info
from app.middleware.request_context import RequestContextManager
from app.services.nl import compaction
from app.services.nl.nl_model import (
    ExtractedParams,
    NLChatRequest,
    NLChatResponse,
    NLMessage,
    NLSession,
)
from app.services.nl.providers import dispatcher
from app.services.nl.repositories.nl_repository import NLRepository

TRIPLE_ASK_WINDOW = 3

BASE_SYSTEM_PROMPT = (
    "You are a helpful assistant that guides a user through defining a new feature flag "
    "for a feature-flag SaaS product. Ask clarifying questions to fill in missing fields: "
    "flag_key (snake_case), name (human-readable), description (optional), default_value, "
    "and cohorts (list of {name, percentage, value}; percentages must sum to exactly 100). "
    "Whenever new info is gathered, call the `update_flag_draft` tool. Call the `confirm_flag` "
    "tool ONLY when the user has explicitly confirmed they want to save the flag (e.g. 'save it', "
    "'looks good, commit', 'yes create it'). Never call confirm_flag without explicit user "
    "confirmation. Keep replies concise and focused on what's still needed."
)


async def chat(request: NLChatRequest) -> NLChatResponse:
    """Handle a single chat turn end-to-end."""
    client_id, user_id = _resolve_identity()
    repository = NLRepository()
    session = await _load_or_create_session(
        repository=repository,
        session_id=request.session_id,
        client_id=client_id,
        user_id=user_id,
    )
    force_action = _is_triple_ask(session.messages, request.message)
    system_prompt = _build_system_prompt(session, force_action=force_action)
    history = _build_history_dicts(session.messages)
    assistant_text, tool_draft, confirm_called, tokens = await dispatcher.chat_turn(
        system_prompt=system_prompt,
        history=history,
        user_message=request.message,
    )
    _merge_extracted(session.extracted, tool_draft)
    user_msg = NLMessage(role="user", content=request.message)
    assistant_msg = NLMessage(role="assistant", content=assistant_text)
    session.messages.extend([user_msg, assistant_msg])
    compacted = False
    if compaction.should_compact(tokens):
        session = await compaction.compact_session(session)
        compacted = True
    committed_flag_id: Optional[str] = None
    if confirm_called and _is_extracted_complete(session.extracted):
        committed_flag_id = await _try_commit_flag(session)
        if committed_flag_id is not None:
            session.status = "committed"
            session.committed_flag_id = committed_flag_id
    await _persist_session_changes(
        repository=repository,
        session=session,
        user_msg=user_msg,
        assistant_msg=assistant_msg,
        compacted=compacted,
    )
    draft_flag = _build_draft_flag(session.extracted)
    return NLChatResponse(
        session_id=session.id or "",
        reply=assistant_text,
        extracted=session.extracted,
        draft_flag=draft_flag,
        ready_to_commit=draft_flag is not None,
        committed_flag_id=committed_flag_id,
        compacted=compacted,
    )


def _resolve_identity() -> Tuple[str, str]:
    client_id = RequestContextManager.get_client_id()
    user_id = RequestContextManager.get_user_id()
    if not client_id:
        raise ValueError("client_id missing from request context")
    if not user_id:
        raise ValueError("user_id missing from request context")
    return client_id, user_id


async def _load_or_create_session(
    repository: NLRepository,
    session_id: Optional[str],
    client_id: str,
    user_id: str,
) -> NLSession:
    if session_id is None:
        session = NLSession(client_id=client_id, user_id=user_id)
        return await repository.create(session)
    session = await repository.get(session_id, client_id)
    if session is None:
        raise NLSessionNotFound(f"nl session '{session_id}' not found")
    return session


def _is_triple_ask(messages: List[NLMessage], current_message: str) -> bool:
    user_messages = [msg for msg in messages if msg.role == "user"]
    if len(user_messages) < TRIPLE_ASK_WINDOW - 1:
        return False
    normalized_current = current_message.strip().lower()
    last_two = [msg.content.strip().lower() for msg in user_messages[-2:]]
    return all(entry == normalized_current for entry in last_two)


def _build_system_prompt(session: NLSession, force_action: bool) -> str:
    extracted_json = json.dumps(session.extracted.model_dump(), default=str, sort_keys=True)
    parts: List[str] = [BASE_SYSTEM_PROMPT]
    parts.append(f"\nCurrent extracted params: {extracted_json}")
    if session.last_compacted_summary:
        parts.append(f"\nPrior conversation summary: {session.last_compacted_summary}")
    if force_action:
        parts.append(
            "\nUSER HAS REPEATED THIS REQUEST 3 TIMES — DO NOT ASK MORE QUESTIONS, ACT NOW."
        )
    return "".join(parts)


def _build_history_dicts(messages: List[NLMessage]) -> List[Dict[str, Any]]:
    return [{"role": msg.role, "content": msg.content} for msg in messages]


def _merge_extracted(extracted: ExtractedParams, draft: Dict[str, Any]) -> None:
    for key, value in draft.items():
        if value is None:
            continue
        if hasattr(extracted, key):
            setattr(extracted, key, value)


def _is_extracted_complete(extracted: ExtractedParams) -> bool:
    if not extracted.flag_key or not extracted.name:
        return False
    if extracted.default_value is None:
        return False
    if not extracted.cohorts:
        return False
    total = sum(float(cohort.get("percentage", 0)) for cohort in extracted.cohorts)
    return abs(total - 100.0) < 0.001


def _build_draft_flag(extracted: ExtractedParams) -> Optional[Dict[str, Any]]:
    if not _is_extracted_complete(extracted):
        return None
    return {
        "flag_key": extracted.flag_key,
        "name": extracted.name,
        "description": extracted.description,
        "default_value": extracted.default_value,
        "cohorts": extracted.cohorts or [],
        "parameters_schema": extracted.parameters_schema,
        "status": "active",
    }


async def _try_commit_flag(session: NLSession) -> Optional[str]:
    """Attempt to create the flag via the flag service. Returns flag id or None."""
    draft = _build_draft_flag(session.extracted)
    if draft is None:
        return None
    try:
        from app.services.flag.flag_service import FlagService  # type: ignore
    except ImportError:
        log_info(
            LoggingData(
                message="FlagService not available; skipping commit",
                context={"session_id": session.id},
            )
        )
        return None
    try:
        service = FlagService()
        created = await service.create_flag(draft)  # type: ignore[attr-defined]
        flag_id = getattr(created, "id", None)
        return flag_id
    except Exception as exc:
        log_error(
            LoggingData(
                message="Failed to commit flag from NL session",
                context={"session_id": session.id},
                error=exc,
            )
        )
        return None


async def _persist_session_changes(
    repository: NLRepository,
    session: NLSession,
    user_msg: NLMessage,
    assistant_msg: NLMessage,
    compacted: bool,
) -> None:
    if session.id is None:
        return
    client_id = session.client_id
    if compacted:
        await repository.replace_messages(
            session_id=session.id,
            client_id=client_id,
            messages=session.messages,
            summary=session.last_compacted_summary or "",
        )
        await repository.update(
            session_id=session.id,
            client_id=client_id,
            updates={
                "extracted": session.extracted.model_dump(),
                "status": session.status,
                "committed_flag_id": session.committed_flag_id,
                "compaction_count": session.compaction_count,
            },
        )
        return
    await repository.append_message(session.id, client_id, user_msg)
    await repository.append_message(session.id, client_id, assistant_msg)
    await repository.update(
        session_id=session.id,
        client_id=client_id,
        updates={
            "extracted": session.extracted.model_dump(),
            "status": session.status,
            "committed_flag_id": session.committed_flag_id,
        },
    )
