"""Progressive skill harness.

A small, dependency-free engine for discovering, routing, and executing
WorkBuddy-style skills using a three-level progressive-disclosure model:

  Level 1 - metadata index (cheap, always in memory)
  Level 2 - SKILL.md body (loaded when a skill is selected / triggered)
  Level 3 - bundled resources (scripts/ references/ assets/ loaded on demand)

The whole point of the harness is that heavier content is only pulled into
memory at the moment it is actually needed.
"""

from .discovery import SkillIndex, SkillMetadata, default_skill_dirs
from .skill import Skill, SkillResource
from .router import Match, route, best
from .loader import ProgressiveLoader, LoadState
from .executor import (
    Executor,
    DryRunExecutor,
    ScriptExecutor,
    ContextExecutor,
    ExecutionPlan,
)
from .frontmatter import parse_frontmatter, parse_frontmatter_file, tokenize

__all__ = [
    "SkillIndex",
    "SkillMetadata",
    "default_skill_dirs",
    "Skill",
    "SkillResource",
    "Match",
    "route",
    "best",
    "ProgressiveLoader",
    "LoadState",
    "Executor",
    "DryRunExecutor",
    "ScriptExecutor",
    "ContextExecutor",
    "ExecutionPlan",
    "parse_frontmatter",
    "parse_frontmatter_file",
    "tokenize",
]
__version__ = "0.1.0"
