"""Sentiment analysis role: label + score."""

import json
import re

from .base import RoleDef, register


def parse_sentiment(raw: str) -> dict:
    try:
        d = json.loads(raw)
        label = str(d.get("label", "neutral")).lower()
        score = float(d.get("score", 0.0))
        return {"label": label, "score": score}
    except (json.JSONDecodeError, TypeError, ValueError):
        m = re.search(r"(positive|negative|neutral)", raw, re.I)
        return {"label": m.group(1).lower() if m else "neutral", "score": 0.0}


register(
    RoleDef(
        name="sentiment",
        system=(
            "ROLE: sentiment\n"
            "You are a sentiment analyzer. Respond with ONLY a JSON object: "
            '{"label": "positive|negative|neutral", "score": float}. No extra text.'
        ),
        build_user=lambda text: f"Analyze the sentiment of the following text.\n\n{text}",
        parse=parse_sentiment,
    )
)
