"""Shared graph state for the NLP orchestrator.

The crucial piece for parallel subagents is the `results` channel: it uses a
custom dict-merge reducer so that the multiple worker branches can all write
to it concurrently without LangGraph raising INVALID_CONCURRENT_GRAPH_UPDATE.
"""

from typing import Annotated, Any, TypedDict


def merge_results(left: dict | None, right: dict | None) -> dict:
    """Merge two partial result dicts. Role keys never collide, so this is safe."""
    return {**(left or {}), **(right or {})}


class TaskResult(TypedDict, total=False):
    ok: bool
    role: str
    data: Any          # parsed structured result (when ok=True)
    error: str         # human-readable error (when ok=False)


class AgentState(TypedDict, total=False):
    text: str                                   # original input text
    tasks: list[str]                            # roles the supervisor decided to run
    results: Annotated[dict, merge_results]     # role -> TaskResult (concurrent writes OK)
    final_report: str                           # Markdown report produced by aggregator
