"""LangGraph orchestration: supervisor -> parallel workers -> aggregator.

The supervisor uses `Command(goto=[Send(...)])` to fan out one task per role.
Because the graph runs via `ainvoke` (async) with an async client, the worker
branches execute concurrently. Every `worker_*` node connects to a single
`aggregator` node, which LangGraph runs exactly once after all branches finish
(fan-in). The aggregator is also the fallback target when there are no tasks.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send

from .config import Settings
from .llm import LLMClient
from .report import render_report
from .roles.base import all_roles
from .state import AgentState
from .worker import make_worker


def build_graph(llm: LLMClient, settings: Settings, roles: list[str] | None = None):
    roles = roles if roles is not None else all_roles()

    async def supervisor(state: AgentState) -> Command:
        targets = state.get("tasks") or roles
        if not targets:
            # Nothing to run: jump straight to the aggregator so it still emits a report.
            return Command(update={"tasks": []}, goto=["aggregator"])
        return Command(
            update={"tasks": targets},
            # Include `text` in the payload: Send overrides the node's input state.
            goto=[Send(f"worker_{r}", {"role": r, "text": state["text"]}) for r in targets],
        )

    def aggregator(state: AgentState) -> dict:
        return {"final_report": render_report(state["text"], state["results"])}

    b = StateGraph(AgentState)
    b.add_node("supervisor", supervisor)
    for r in roles:
        b.add_node(f"worker_{r}", make_worker(llm, settings, r))
    b.add_node("aggregator", aggregator)

    b.add_edge(START, "supervisor")
    for r in roles:
        b.add_edge(f"worker_{r}", "aggregator")  # all workers -> aggregator = fan-in
    b.add_edge("aggregator", END)
    return b.compile()
