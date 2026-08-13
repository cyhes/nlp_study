"""The generic parallel worker.

One worker node is created per role (via `make_worker`). Each worker:

  1. builds the role's prompt,
  2. calls the LLM with `asyncio.wait_for` (per-attempt timeout),
  3. retries transient errors with exponential backoff (`tenacity`),
  4. parses the response.

CRITICAL for fault isolation: the worker NEVER raises. Any failure (timeout,
retry exhaustion, parse error, network error) is caught and stored in the
returned `TaskResult` with `ok=False`. This prevents LangGraph from cancelling
sibling branches and collapsing the whole run.
"""

import asyncio

import tenacity
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

from .config import Settings
from .roles.base import get_role
from .state import AgentState, TaskResult


def _build_attempt(settings: Settings):
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(settings.max_retries),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=settings.max_backoff),
        retry=tenacity.retry_if_exception_type(
            (
                RateLimitError,
                APIConnectionError,
                APITimeoutError,
                asyncio.TimeoutError,
                APIError,
            )
        ),
        reraise=True,  # surface the real exception so the worker can record it
    )
    async def _attempt(role_def, text, llm):
        messages = [
            {"role": "system", "content": role_def.system},
            {"role": "user", "content": role_def.build_user(text)},
        ]
        raw = await asyncio.wait_for(llm.chat(messages), timeout=settings.per_task_timeout)
        return role_def.parse(raw)

    return _attempt


def make_worker(llm, settings: Settings, role: str):
    attempt = _build_attempt(settings)

    async def worker(state: AgentState) -> dict:
        role_def = get_role(role)
        try:
            data = await attempt(role_def, state["text"], llm)
            result: TaskResult = {"ok": True, "role": role, "data": data}
        except Exception as e:  # swallow everything -> sibling branches survive
            result = {"ok": False, "role": role, "error": f"{type(e).__name__}: {e}"}
        # Written through the merge_results reducer, so concurrent workers are safe.
        return {"results": {role: result}}

    return worker
