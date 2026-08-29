"""Importing this package registers all built-in roles.

The sibling modules register themselves on import via `register(...)`. We import
them here (in a stable order) so that any `import orchestrator.roles` populates
the registry. `DEFAULT_ROLES` exposes the resulting role list.
"""

from . import classification, ner, sentiment, summarization, translation  # noqa: F401
from .base import RoleDef, all_roles, get_role, register

DEFAULT_ROLES = all_roles()

__all__ = [
    "RoleDef",
    "register",
    "get_role",
    "all_roles",
    "DEFAULT_ROLES",
]
