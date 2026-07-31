"""Level-2 / Level-3 skill representation with lazy loading.

A :class:`Skill` wraps :class:`~harness.discovery.SkillMetadata` and loads its
heavy content only when asked:

* ``load_body()``      -> Level 2 (full ``SKILL.md`` markdown)
* ``load_reference()`` -> Level 3 (a single ``references/`` file, read on demand)
* ``run_script()``     -> Level 3 (execute a bundled script via subprocess)

Entry-script resolution is intentionally forgiving, because real-world skills
are inconsistent about layout: an entry may be declared in frontmatter
(``entry:``), referenced from the body (e.g. a ``scraper.py`` path inside a
bash block), placed at the skill root, or live under ``scripts/``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .discovery import SkillMetadata
from .frontmatter import parse_frontmatter_file

# Extensions we treat as directly-runnable scripts at the skill root.
EXECUTABLE_EXTENSIONS = {
    ".py", ".sh", ".bash", ".js", ".bat", ".cmd", ".ps1", ".rb", ".pl",
}
PREFERRED_SCRIPTS = ("scraper.py", "main.py", "run.py", "entry.py")
# Matches a .py path referenced inside the body (e.g. ".../scraper.py").
_BODY_SCRIPT_RE = re.compile(r"[A-Za-z0-9_./\\-]+\.py")
# Matches a python interpreter referenced inside the body, e.g.
# "C:/Program Files/Python312/python.exe" or "python3".
_BODY_INTERP_RE = re.compile(r'(?:"([^"]*python\.exe)"|(\S*python3?))(?:\.exe)?')


@dataclass
class SkillResource:
    kind: str  # "script" | "reference" | "asset"
    name: str  # relative path inside the skill dir, e.g. "scripts/greet.py" or "scraper.py"
    abs_path: Path


class Skill:
    def __init__(self, meta: SkillMetadata):
        self.meta = meta
        self._body: str | None = None
        self._frontmatter: dict | None = None
        self._resources: list[SkillResource] | None = None
        self._loaded_references: dict[str, str] = {}

    # ---- Level 2: body -------------------------------------------------
    @property
    def loaded_level(self) -> int:
        return 2 if self._body is not None else 1

    def load_body(self) -> str:
        if self._body is None:
            fm = parse_frontmatter_file(self.meta.skill_md)
            self._frontmatter = fm.data
            self._body = fm.body
        return self._body

    @property
    def body(self) -> str:
        return self.load_body()

    @property
    def frontmatter(self) -> dict:
        if self._frontmatter is None:
            self.load_body()
        return self._frontmatter  # type: ignore[return-value]

    @property
    def entry(self) -> str | None:
        """Explicit entry declared in frontmatter (``entry:``)."""
        return self.frontmatter.get("entry")

    @property
    def interpreter(self) -> str | None:
        """Preferred interpreter for .py scripts.

        Resolution order: frontmatter ``interpreter:`` -> python path
        referenced in the body -> managed ``sys.executable``.
        """
        interp = self.frontmatter.get("interpreter")
        if interp:
            return str(interp)
        m = _BODY_INTERP_RE.search(self.body)
        if m:
            return (m.group(1) or m.group(2) or "").strip()
        return None

    # ---- Level 3: resources -------------------------------------------
    def scan_resources(self) -> list[SkillResource]:
        if self._resources is not None:
            return self._resources
        self._resources = []
        # Bundled sub-directories.
        for kind, folder in (
            ("script", "scripts"),
            ("reference", "references"),
            ("asset", "assets"),
        ):
            base = self.meta.path / folder
            if base.is_dir():
                for p in sorted(base.rglob("*")):
                    if p.is_file():
                        rel = f"{folder}/{p.relative_to(base).as_posix()}"
                        self._resources.append(SkillResource(kind, rel, p.resolve()))
        # Root-level runnable scripts (e.g. legacy skills with scraper.py at root).
        for p in sorted(self.meta.path.iterdir()):
            if p.is_file() and p.suffix.lower() in EXECUTABLE_EXTENSIONS:
                self._resources.append(SkillResource("script", p.name, p.resolve()))
        return self._resources

    def resources(self, kind: str | None = None) -> list[SkillResource]:
        rs = self.scan_resources()
        return [r for r in rs if kind is None or r.kind == kind]

    def load_reference(self, name: str) -> str:
        if name in self._loaded_references:
            return self._loaded_references[name]
        target: Path | None = None
        for r in self.resources("reference"):
            if r.name == name or r.name == f"references/{name}" or r.name.endswith(f"/{name}"):
                target = r.abs_path
                break
        if target is None or not target.is_file():
            raise FileNotFoundError(f"reference not found: {name}")
        text = target.read_text(encoding="utf-8")
        self._loaded_references[name] = text
        return text

    # ---- Entry resolution ---------------------------------------------
    def entry_script(self) -> str | None:
        """Resolve which script to run, tolerant of real-world layouts.

        1. frontmatter ``entry:``
        2. a ``.py`` path referenced in the body
        3. a preferred script name at the skill root
        4. any script at the skill root
        5. a preferred / first script under ``scripts/``
        """
        if self.entry:
            return self.entry
        m = _BODY_SCRIPT_RE.search(self.body)
        if m:
            return m.group(0)
        root_scripts = [r for r in self.resources("script") if "/" not in r.name]
        for pref in PREFERRED_SCRIPTS:
            for r in root_scripts:
                if r.name == pref:
                    return r.name
        if root_scripts:
            return root_scripts[0].name
        folder_scripts = self.resources("script")
        for pref in PREFERRED_SCRIPTS:
            for s in folder_scripts:
                if s.name.endswith(pref):
                    return s.name
        if folder_scripts:
            return folder_scripts[0].name
        return None

    def run_script(
        self,
        name: str | None = None,
        args: list[str] | None = None,
        capture: bool = True,
    ) -> subprocess.CompletedProcess:
        """Execute a bundled script (Level-3 side effect)."""
        if name is None:
            name = self.entry_script()
        if name is None:
            raise RuntimeError("no script to run (no entry, body ref, or scripts found)")
        target: Path | None = None
        for r in self.resources("script"):
            if r.name == name or r.name.endswith(f"/{name}"):
                target = r.abs_path
                break
        if target is None or not target.is_file():
            raise FileNotFoundError(f"script not found: {name}")
        cmd = self._build_command(target, args or [], interpreter=self.interpreter)
        return subprocess.run(
            cmd, capture_output=capture, text=True, cwd=str(self.meta.path)
        )

    @staticmethod
    def _build_command(
        target: Path, args: list[str], interpreter: str | None = None
    ) -> list[str]:
        suffix = target.suffix.lower()
        if suffix == ".py":
            exe = interpreter or sys.executable
            return [exe, str(target), *args]
        if suffix in (".sh", ".bash"):
            return ["bash", str(target), *args]
        if suffix == ".js":
            return ["node", str(target), *args]
        if suffix in (".cmd", ".bat"):
            return ["cmd", "/c", str(target), *args]
        if suffix == ".ps1":
            return ["powershell", "-File", str(target), *args]
        return [str(target), *args]  # best-effort direct execution

    @classmethod
    def from_metadata(cls, meta: SkillMetadata) -> "Skill":
        return cls(meta)
