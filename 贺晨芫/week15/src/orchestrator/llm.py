"""LLM client abstraction.

Workers depend only on the `LLMClient.chat(messages) -> str` protocol. Two
implementations are provided:

  * `OpenAILLM`  - real OpenAI-compatible backend (DeepSeek by default).
  * `MockLLM`    - deterministic offline responder for demos and tests.

A single client instance is shared across all parallel workers (the underlying
httpx connection pool overlaps I/O for real concurrency).
"""

import asyncio
import re

from openai import AsyncOpenAI

from .config import Settings


class LLMClient:
    async def chat(self, messages: list[dict]) -> str:
        raise NotImplementedError

    async def aclose(self) -> None:
        raise NotImplementedError


class OpenAILLM(LLMClient):
    def __init__(self, s: Settings):
        self._client = AsyncOpenAI(base_url=s.base_url, api_key=s.api_key or "missing")
        self._model = s.model_name

    async def chat(self, messages: list[dict]) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0,
        )
        return resp.choices[0].message.content or ""

    async def aclose(self) -> None:
        await self._client.close()


# Deterministic mock answers keyed by the role name embedded in the system prompt.
MOCK_RESPONSES: dict[str, str] = {
    "classification": '{"topic": "technology", "intent": "inform"}',
    "ner": '{"entities": [{"text": "Apple", "type": "ORG"}, '
           '{"text": "Beijing", "type": "LOC"}, '
           '{"text": "Alice", "type": "PER"}]}',
    "summarization": '{"summary": "A major company is exploring an acquisition that the market welcomed."}',
    "sentiment": '{"label": "positive", "score": 0.87}',
    "translation": '{"target_lang": "en", "translation": "Apple plans to buy a Beijing startup for $1B."}',
}


class MockLLM(LLMClient):
    """Offline responder. Sleeps a little so tests can prove *parallel* execution."""

    def __init__(self, latency: float = 0.05):
        self.latency = latency
        self.call_count = 0

    async def chat(self, messages: list[dict]) -> str:
        self.call_count += 1
        await asyncio.sleep(self.latency)
        sys_content = messages[0]["content"]
        m = re.search(r"ROLE:\s*(\w+)", sys_content)
        role = m.group(1) if m else "unknown"
        return MOCK_RESPONSES.get(role, "{}")

    async def aclose(self) -> None:
        pass


def get_llm(s: Settings | None = None) -> LLMClient:
    s = s or Settings(
        api_key=None, base_url="https://api.deepseek.com",
        model_name="deepseek-chat", per_task_timeout=30.0,
        max_retries=3, max_backoff=8.0, use_mock=True,
    )
    return MockLLM() if s.use_mock else OpenAILLM(s)
