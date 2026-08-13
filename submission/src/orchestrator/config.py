"""Configuration loaded from environment variables.

All knobs (DeepSeek endpoint, model name, timeouts, retries) are env-driven so
the code itself stays free of secrets and hardcoded values.
"""

from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    base_url: str
    model_name: str
    per_task_timeout: float
    max_retries: int
    max_backoff: float
    use_mock: bool


def load_settings() -> Settings:
    load_dotenv()
    api_key = (
        __import__("os").getenv("DEEPSEEK_API_KEY")
        or __import__("os").getenv("OPENAI_API_KEY")
    )
    import os

    return Settings(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        # Default to deepseek-chat; override with e.g. MODEL_NAME=deepseek-v4-flash
        model_name=os.getenv("MODEL_NAME", "deepseek-chat"),
        per_task_timeout=float(os.getenv("NLP_TIMEOUT", "30")),
        max_retries=int(os.getenv("NLP_MAX_RETRIES", "3")),
        max_backoff=float(os.getenv("NLP_MAX_BACKOFF", "8")),
        # Force mock when explicitly requested OR when no key is available.
        use_mock=os.getenv("NLP_USE_MOCK") == "1" or not api_key,
    )
