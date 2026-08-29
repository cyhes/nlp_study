"""Role registry.

A `RoleDef` is *data*, not topology: adding a new NLP subagent is just a matter
of registering one more `RoleDef` (see the sibling modules). The supervisor/graph
never need to change.
"""

from dataclasses import dataclass
from typing import Any, Callable

from orchestrator.state import TaskResult  # noqa: F401  (re-exported for convenience)


@dataclass
class RoleDef:
    name: str
    system: str
    build_user: Callable[[str], str]
    parse: Callable[[str], Any]


_REGISTRY: dict[str, RoleDef] = {}


def register(r: RoleDef) -> RoleDef:
    _REGISTRY[r.name] = r
    return r


def get_role(name: str) -> RoleDef:
    if name not in _REGISTRY:
        raise KeyError(f"unknown role: {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def all_roles() -> list[str]:
    return list(_REGISTRY)
