"""Shared pytest fixtures."""

import pytest

from orchestrator.llm import MockLLM


@pytest.fixture
def mock_llm():
    """A fresh offline LLM responder with a small latency for parallel tests."""
    return MockLLM(latency=0.05)
