"""Named-entity recognition role: persons, orgs, locations, etc."""

import json
import re

from .base import RoleDef, register


def parse_ner(raw: str) -> dict:
    try:
        d = json.loads(raw)
        ents = d.get("entities", [])
        if isinstance(ents, list):
            return {
                "entities": [
                    {"text": e.get("text"), "type": e.get("type")}
                    for e in ents
                    if isinstance(e, dict)
                ]
            }
        return {"entities": []}
    except json.JSONDecodeError:
        # Fallback: match "Text (TYPE)" patterns.
        found = re.findall(r"([\w一-鿿]+)\s*\(([A-Z]+)\)", raw)
        return {"entities": [{"text": t, "type": ty} for t, ty in found]}


register(
    RoleDef(
        name="ner",
        system=(
            "ROLE: ner\n"
            "You are a named-entity recognizer. Respond with ONLY a JSON object: "
            '{"entities": [{"text": str, "type": str}]}. No extra text.'
        ),
        build_user=lambda text: (
            "Extract named entities (person, organization, location, misc) "
            f"from the text.\n\n{text}"
        ),
        parse=parse_ner,
    )
)
