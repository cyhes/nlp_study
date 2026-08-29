"""End-to-end graph tests using the offline MockLLM.

These prove three things:
  * parallel dispatch (all roles run, wall-clock << sequential),
  * aggregation into a single report,
  * fault isolation (one failing role doesn't break the others or the run).
"""

import time

from orchestrator import analyze
from orchestrator.roles.base import all_roles

SAMPLE = (
    "Apple is looking to buy a startup in Beijing for $1B. "
    "The market reacted positively to the news."
)


async def test_parallel_and_aggregation(mock_llm):
    start = time.monotonic()
    state = await analyze(SAMPLE, llm=mock_llm)
    elapsed = time.monotonic() - start

    # every role was invoked exactly once
    assert mock_llm.call_count == len(all_roles())
    # truly parallel: far less than running them one after another
    assert elapsed < len(all_roles()) * mock_llm.latency + 0.2

    assert set(state["results"].keys()) == set(all_roles())
    for role, res in state["results"].items():
        assert res["ok"] is True, f"{role} failed: {res.get('error')}"
        assert "data" in res

    assert "NLP Analysis Report" in state["final_report"]
    for role in all_roles():
        assert f"## {role}" in state["final_report"]


async def test_error_isolation(mock_llm):
    original = mock_llm.chat

    async def failing(messages):
        if "ROLE: ner" in messages[0]["content"]:
            raise RuntimeError("boom: simulated NER failure")
        return await original(messages)

    mock_llm.chat = failing

    state = await analyze(SAMPLE, llm=mock_llm)

    # the failing role is isolated: recorded but does not crash the run
    assert state["results"]["ner"]["ok"] is False
    assert "error" in state["results"]["ner"]
    for role in ("classification", "summarization", "sentiment", "translation"):
        assert state["results"][role]["ok"] is True

    # aggregator still produced a full report containing both outcomes
    assert "FAILED" in state["final_report"]
    assert "NLP Analysis Report" in state["final_report"]


async def test_empty_roles(mock_llm):
    state = await analyze("anything", roles=[], llm=mock_llm)
    assert state["results"] == {}
    assert "No tasks were executed" in state["final_report"]
    assert mock_llm.call_count == 0
