"""Public API for the parallel NLP subagent orchestrator.

Library usage:
    from orchestrator import analyze, analyze_sync

    result = analyze_sync("Some text here.")            # runs all roles
    result = analyze_sync(text, roles=["ner", "sentiment"])

    # async
    result = await analyze(text, llm=custom_llm)
"""

import asyncio
from typing import Any

from .config import Settings, load_settings
from .graph import build_graph
from .llm import LLMClient, get_llm
from .state import AgentState

__all__ = ["analyze", "analyze_sync", "load_settings", "get_llm"]


async def analyze(
    text: str,
    *,
    roles: list[str] | None = None,
    llm: LLMClient | None = None,
    settings: Settings | None = None,
) -> dict:
    """Run the orchestrator on `text` and return the final `AgentState` dict.

    Workers run in parallel (async). Pass your own `llm` to inject a mock or
    custom backend; otherwise one is created from env config and closed here.
    """
    settings = settings or load_settings()
    own_llm = llm is None
    llm = llm or get_llm(settings)
    try:
        graph = build_graph(llm, settings, roles)
        state: AgentState = {
            "text": text,
            "tasks": roles or [],
            "results": {},
            "final_report": "",
        }
        return await graph.ainvoke(state, config={"recursion_limit": 50})
    finally:
        if own_llm:
            await llm.aclose()


def analyze_sync(text: str, **kw: Any) -> dict:
    """Blocking wrapper around `analyze` (used by the CLI)."""
    return asyncio.run(analyze(text, **kw))
