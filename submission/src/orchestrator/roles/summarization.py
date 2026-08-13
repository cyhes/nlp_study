"""Summarization role: concise one/two-sentence summary."""

import json

from .base import RoleDef, register


def parse_summary(raw: str) -> dict:
    raw = (raw or "").strip()
    if raw.startswith("{"):
        try:
            d = json.loads(raw)
            summary = d.get("summary", raw)
            return {"summary": summary if isinstance(summary, str) else raw}
        except json.JSONDecodeError:
            pass
    return {"summary": raw}


register(
    RoleDef(
        name="summarization",
        system=(
            "ROLE: summarization\n"
            "You are a summarizer. Respond with a concise summary as plain text, "
            'or JSON {"summary": str}.'
        ),
        build_user=lambda text: (
            f"Summarize the following text in one or two sentences.\n\n{text}"
        ),
        parse=parse_summary,
    )
)
