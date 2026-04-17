"""LLM provider implementations for the NL flag builder.

Each provider exposes the same ``chat_turn`` and ``summarize_for_compaction``
contract so the NL service code is provider-agnostic. Selection happens in
``dispatcher.py`` based on ``settings.nl_provider``.
"""
