"""Text classification role: topic + intent labels."""

import json
import re

from .base import RoleDef, register


def parse_classification(raw: str) -> dict:
    try:
        d = json.loads(raw)
        return {
            "topic": str(d.get("topic", "unknown")),
            "intent": str(d.get("intent", "unknown")),
        }
    except json.JSONDecodeError:
        m = re.search(r"topic[:=]\s*([\w\-]+)", raw, re.I)
        n = re.search(r"intent[:=]\s*([\w\-]+)", raw, re.I)
        return {
            "topic": m.group(1) if m else "unknown",
            "intent": n.group(1) if n else "unknown",
        }


register(
    RoleDef(
        name="classification",
        system=(
            "ROLE: classification\n"
            "You are a text classifier. Respond with ONLY a JSON object: "
            '{"topic": str, "intent": str}. No extra text.'
        ),
        build_user=lambda text: f"Classify the following text by topic and intent.\n\n{text}",
        parse=parse_classification,
    )
)
