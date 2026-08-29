"""Level-1 discovery: scan skill directories and build a lightweight index.

Only the YAML frontmatter at the top of each ``SKILL.md`` is read (bounded
head), so the index stays cheap even when skills carry large bodies or big
bundled resources.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from .frontmatter import parse_frontmatter_head


@dataclass
class SkillMetadata:
    """Level-1 representation: metadata only, no body, no resources."""

    name: str
    description: str
    path: Path  # absolute path to the skill directory
    skill_md: Path  # absolute path to SKILL.md
    location: str  # "user" | "project" | "example" | "extra"
    agent_created: bool
    frontmatter: dict

    @property
    def level(self) -> int:
        # This object is metadata-only, i.e. Level 1.
        return 1


class SkillIndex:
    """Read-only registry of discovered skills (metadata only)."""

    def __init__(self, metas: Iterable[SkillMetadata]):
        self._metas: dict[str, SkillMetadata] = {}
        for m in metas:
            self._metas[m.name] = m

    @classmethod
    def discover(cls, dirs: Iterable[Path]) -> "SkillIndex":
        metas: list[SkillMetadata] = []
        for d in dirs:
            d = Path(d)
            if not d.is_dir():
                continue
            for sub in sorted(d.iterdir()):
                if not sub.is_dir():
                    continue
                sk = sub / "SKILL.md"
                if not sk.is_file():
                    continue
                fm = parse_frontmatter_head(sk)
                name = fm.get("name") or sub.name
                location = fm.get("location") or _infer_location(d)
                metas.append(
                    SkillMetadata(
                        name=name,
                        description=fm.get("description", ""),
                        path=sub.resolve(),
                        skill_md=sk.resolve(),
                        location=location,
                        agent_created=bool(fm.get("agent_created", False)),
                        frontmatter=fm,
                    )
                )
        return cls(metas)

    def __iter__(self) -> Iterator[SkillMetadata]:
        return iter(self._metas.values())

    def __len__(self) -> int:
        return len(self._metas)

    def names(self) -> list[str]:
        return list(self._metas)

    def get(self, name: str) -> SkillMetadata | None:
        return self._metas.get(name)

    def items(self):
        return self._metas.items()


def _infer_location(d: Path) -> str:
    s = str(d).lower().replace("\\", "/")
    if s.endswith("/.workbuddy/skills"):
        parent = d.parent.parent.name.lower()
        return "user" if parent == ".workbuddy" else "project"
    return "extra"


def default_skill_dirs(workspace: Path | None = None) -> list[Path]:
    """Standard skill search paths.

    Order: user-level (``~/.workbuddy/skills``) then project-level
    (``<workspace>/.workbuddy/skills``).
    """
    dirs: list[Path] = []
    dirs.append(Path.home() / ".workbuddy" / "skills")
    ws = Path(workspace) if workspace else Path.cwd()
    dirs.append(ws / ".workbuddy" / "skills")
    return dirs
