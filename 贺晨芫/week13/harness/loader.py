"""Progressive loader: orchestrates the L1 -> L2 -> L3 transitions.

This is the single place that decides *when* heavier content is pulled into
memory, and it records the current level per skill so callers (and the CLI)
can observe and demonstrate the progressive behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .discovery import SkillIndex, SkillMetadata
from .router import Match, best, route
from .skill import Skill


@dataclass
class LoadState:
    level: int = 1  # 1 metadata, 2 body loaded, 3 resources used
    loaded_references: list[str] = field(default_factory=list)
    ran_scripts: list[str] = field(default_factory=list)


class ProgressiveLoader:
    def __init__(self, index: SkillIndex):
        self.index = index
        self._skills: dict[str, Skill] = {}
        self._state: dict[str, LoadState] = {}

    # ---- Level 2 -------------------------------------------------------
    def select(self, name: str) -> Skill:
        """Load a skill's body on demand (Level 2)."""
        if name not in self._skills:
            meta = self.index.get(name)
            if meta is None:
                raise KeyError(f"skill not found: {name}")
            self._skills[name] = Skill.from_metadata(meta)
            self._state[name] = LoadState(level=2)
        return self._skills[name]

    def select_best(
        self, query: str, threshold: float = 0.15
    ) -> Optional[tuple[Match, Skill]]:
        m = best(query, self.index, threshold=threshold)
        if m is None:
            return None
        return m, self.select(m.metadata.name)

    def candidates(self, query: str, top_k: int = 3) -> list[Match]:
        return route(query, self.index, top_k=top_k)

    # ---- Level 3 -------------------------------------------------------
    def load_reference(self, skill: Skill, name: str) -> str:
        text = skill.load_reference(name)
        st = self._state.setdefault(skill.meta.name, LoadState(level=3))
        st.level = 3
        if name not in st.loaded_references:
            st.loaded_references.append(name)
        return text

    def run_script(
        self, skill: Skill, name: str | None = None, args: list[str] | None = None
    ):
        proc = skill.run_script(name, args)
        st = self._state.setdefault(skill.meta.name, LoadState(level=3))
        st.level = 3
        ran = name or skill.entry or "(default)"
        if ran not in st.ran_scripts:
            st.ran_scripts.append(ran)
        return proc

    def state(self, name: str) -> LoadState:
        return self._state.get(name, LoadState(level=1))

    def summary(self) -> dict:
        return {
            name: {
                "level": s.level,
                "references": s.loaded_references,
                "scripts": s.ran_scripts,
            }
            for name, s in self._state.items()
        }
