"""Executors turn a loaded skill into an action.

Three strategies are provided:

* ``DryRunExecutor``  - report what *would* happen, no side effects (safe default)
* ``ScriptExecutor``  - actually run the entry script via subprocess
* ``ContextExecutor`` - assemble body + selected references as a context
  payload for an agent / LLM to act on (instruction-style skills)
"""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .skill import Skill


@dataclass
class ExecutionPlan:
    skill_name: str
    entry_script: str | None
    scripts: list[str]
    references: list[str]
    assets: list[str]
    body_excerpt: str

    def render(self) -> str:
        lines = [f"# Execution plan: {self.skill_name}", ""]
        if self.entry_script:
            lines.append(f"- entry script : {self.entry_script}")
        if self.scripts:
            lines.append(f"- scripts ({len(self.scripts)}): " + ", ".join(self.scripts))
        if self.references:
            lines.append(
                f"- references ({len(self.references)}): " + ", ".join(self.references)
            )
        if self.assets:
            lines.append(f"- assets ({len(self.assets)}): " + ", ".join(self.assets))
        lines.append(f"- body length : {len(self.body_excerpt)} chars")
        return "\n".join(lines)


class Executor(ABC):
    @staticmethod
    def plan(skill: Skill) -> ExecutionPlan:
        skill.load_body()  # ensure Level 2
        scripts = [r.name for r in skill.resources("script")]
        refs = [r.name for r in skill.resources("reference")]
        assets = [r.name for r in skill.resources("asset")]
        entry = skill.entry_script()
        return ExecutionPlan(
            skill_name=skill.meta.name,
            entry_script=entry,
            scripts=scripts,
            references=refs,
            assets=assets,
            body_excerpt=skill.body[:4000],
        )

    @abstractmethod
    def execute(self, skill: Skill, approve: bool = False) -> Any:
        ...


class DryRunExecutor(Executor):
    def execute(self, skill: Skill, approve: bool = False) -> str:
        return self.plan(skill).render()


class ScriptExecutor(Executor):
    def __init__(self, default_approve: bool = False):
        self.default_approve = default_approve

    def execute(
        self, skill: Skill, approve: bool = False
    ) -> subprocess.CompletedProcess:
        plan = self.plan(skill)
        if not plan.entry_script:
            raise RuntimeError(f"{skill.meta.name}: no entry script to run")
        if not (approve or self.default_approve):
            raise PermissionError(
                f"refusing to run {plan.entry_script} without approval; "
                "pass approve=True"
            )
        return skill.run_script(plan.entry_script)


class ContextExecutor(Executor):
    """Assemble a context payload (body + selected references) for an agent."""

    def __init__(self, load_references: bool = True):
        self.load_references = load_references

    def execute(self, skill: Skill, approve: bool = False) -> dict:
        skill.load_body()
        ctx: dict[str, Any] = {
            "name": skill.meta.name,
            "description": skill.meta.description,
            "body": skill.body,
            "references": {},
            "scripts": [r.name for r in skill.resources("script")],
            "assets": [r.name for r in skill.resources("asset")],
        }
        if self.load_references:
            for r in skill.resources("reference"):
                try:
                    ctx["references"][r.name] = skill.load_reference(r.name)
                except Exception as e:  # pragma: no cover - defensive
                    ctx["references"][r.name] = f"<error: {e}>"
        return ctx
