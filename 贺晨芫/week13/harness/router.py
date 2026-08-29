"""Query routing: pick the best skill(s) from a Level-1 index.

Scoring is transparent and dependency-free, combining a name match, a
description token-overlap score (Jaccard over latin words + CJK bigrams), and
phrase containment. This is enough to route a natural-language query to the
right skill without an embedding model.
"""

from __future__ import annotations

from dataclasses import dataclass

from .discovery import SkillIndex, SkillMetadata
from .frontmatter import tokenize


@dataclass
class Match:
    metadata: SkillMetadata
    score: float
    reasons: list[str]

    def __str__(self) -> str:
        return (
            f"{self.metadata.name}  score={self.score:.3f}  "
            + ", ".join(self.reasons)
        )


def _score(query: str, meta: SkillMetadata) -> tuple[float, list[str]]:
    q = tokenize(query)
    if not q:
        return 0.0, []
    d = tokenize(meta.description)
    n = tokenize(meta.name.replace("-", " ").replace("_", " "))

    overlap_d = q & d
    overlap_n = q & n
    # Query coverage (recall): fraction of query tokens present in the
    # skill's description. This is the right signal for routing — a long
    # description must not dilute the score the way Jaccard would.
    coverage = len(overlap_d) / len(q) if q else 0.0
    name_hit = len(overlap_n) / len(q) if q else 0.0

    phrase = 0.0
    ql = query.lower()
    dl = meta.description.lower()
    nl = meta.name.lower().replace("-", " ")
    if ql in dl or dl in ql:
        phrase = 0.3
    if ql in nl or nl in ql:
        phrase = 0.5

    score = 0.55 * coverage + 0.35 * name_hit + phrase
    reasons: list[str] = []
    if overlap_d:
        reasons.append(f"描述命中{len(overlap_d)}/{len(q)}词")
    if overlap_n:
        reasons.append(f"名称命中{len(overlap_n)}词")
    if phrase:
        reasons.append("短语包含")
    return min(score, 1.0), reasons


def route(
    query: str, index: SkillIndex, top_k: int = 3, threshold: float = 0.05
) -> list[Match]:
    results: list[Match] = []
    for m in index:
        s, r = _score(query, m)
        if s >= threshold:
            results.append(Match(m, s, r))
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_k]


def best(query: str, index: SkillIndex, threshold: float = 0.15) -> Match | None:
    matches = route(query, index, top_k=1, threshold=threshold)
    return matches[0] if matches else None
