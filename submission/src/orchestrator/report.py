"""Render the aggregated `results` into a human-readable Markdown report.

Both successes (structured JSON) and failures (error message) are preserved,
so the report always reflects the full outcome of the parallel run.
"""

import json


def render_report(text: str, results: dict) -> str:
    lines = ["# NLP Analysis Report", ""]
    snippet = text.strip().replace("\n", " ")
    if len(snippet) > 200:
        snippet = snippet[:200] + "…"
    lines.append(f"> Input: {snippet}")
    lines.append("")

    if not results:
        lines.append("_No tasks were executed._")
        return "\n".join(lines)

    for role, res in results.items():
        lines.append(f"## {role}")
        if res.get("ok"):
            lines.append("```json")
            lines.append(json.dumps(res.get("data"), ensure_ascii=False, indent=2))
            lines.append("```")
        else:
            lines.append(f"**FAILED**: {res.get('error')}")
        lines.append("")

    return "\n".join(lines)
