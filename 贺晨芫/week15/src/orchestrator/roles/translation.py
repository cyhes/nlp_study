"""Translation role: translate the input into English."""

import json

from .base import RoleDef, register


def parse_translation(raw: str) -> dict:
    raw = (raw or "").strip()
    try:
        d = json.loads(raw)
        return {
            "target_lang": str(d.get("target_lang", "en")),
            "translation": d.get("translation", raw),
        }
    except json.JSONDecodeError:
        return {"target_lang": "en", "translation": raw}


register(
    RoleDef(
        name="translation",
        system=(
            "ROLE: translation\n"
            "You are a translator. Respond with ONLY a JSON object: "
            '{"target_lang": str, "translation": str}. No extra text.'
        ),
        build_user=lambda text: f"Translate the following text into English.\n\n{text}",
        parse=parse_translation,
    )
)
