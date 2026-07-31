"""Command-line interface for the progressive skill harness.

Examples
--------
    python -m harness.cli list
    python -m harness.cli find "抖音 搜索指数"
    python -m harness.cli load douyin-keyword-scraper
    python -m harness.cli run hello-skill --dry
    python -m harness.cli run hello-skill --yes
    python -m harness.cli context hello-skill --include-examples
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .discovery import SkillIndex, default_skill_dirs
from .loader import ProgressiveLoader
from .executor import DryRunExecutor, ScriptExecutor, ContextExecutor


def _build_index(args: argparse.Namespace) -> SkillIndex:
    dirs = list(
        default_skill_dirs(Path(args.workspace) if args.workspace else None)
    )
    for d in args.skills_dir or []:
        dirs.append(Path(d))
    if args.include_examples:
        examples = Path(__file__).resolve().parent.parent / "examples"
        if examples.is_dir():
            dirs.append(examples)
    return SkillIndex.discover(dirs)


def cmd_list(args: argparse.Namespace) -> int:
    idx = _build_index(args)
    print(f"Discovered {len(idx)} skill(s) [Level 1: metadata only]\n")
    for m in idx:
        print(f"  - {m.name}  [{m.location}]")
        print(f"      {m.description}")
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    idx = _build_index(args)
    matches = ProgressiveLoader(idx).candidates(args.query, top_k=args.top_k)
    if not matches:
        print("No matching skill found.")
        return 1
    print(f"Query: {args.query}\n")
    for i, mt in enumerate(matches, 1):
        print(f"  {i}. {mt.metadata.name}  score={mt.score:.3f}")
        for r in mt.reasons:
            print(f"       - {r}")
    return 0


def cmd_load(args: argparse.Namespace) -> int:
    idx = _build_index(args)
    loader = ProgressiveLoader(idx)
    skill = loader.select(args.name)
    print(f"Loaded (Level 2): {skill.meta.name}")
    print(f"  description: {skill.meta.description}")
    print(f"  body chars : {len(skill.body)}")
    print("  resources (Level 3, available on demand):")
    for kind in ("script", "reference", "asset"):
        rs = skill.resources(kind)
        if rs:
            print(f"    {kind}s: " + ", ".join(r.name for r in rs))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    idx = _build_index(args)
    loader = ProgressiveLoader(idx)
    skill = loader.select(args.name)
    if args.dry:
        print(DryRunExecutor().execute(skill))
        return 0
    proc = ScriptExecutor().execute(skill, approve=args.yes)
    print(proc.stdout or "", end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    return proc.returncode


def cmd_context(args: argparse.Namespace) -> int:
    idx = _build_index(args)
    loader = ProgressiveLoader(idx)
    skill = loader.select(args.name)
    ctx = ContextExecutor(load_references=not args.no_refs).execute(skill)
    if args.json:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
    else:
        print(f"# Skill context: {ctx['name']}\n")
        print(ctx["body"])
        if ctx["references"]:
            print("\n## Loaded references\n")
            for name, text in ctx["references"].items():
                print(f"### {name}\n{text}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="harness",
        description="Progressive skill loading & execution harness",
    )
    p.add_argument("--workspace", help="workspace root for project-level skills")
    p.add_argument(
        "--skills-dir", action="append", help="extra skill directory (repeatable)"
    )
    p.add_argument(
        "--include-examples",
        action="store_true",
        help="include the bundled examples/ skills",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("list", help="list discovered skills (Level 1)")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("find", help="route a query to candidate skills")
    sp.add_argument("query")
    sp.add_argument("--top-k", type=int, default=3)
    sp.set_defaults(func=cmd_find)

    sp = sub.add_parser(
        "load", help="load a skill body (Level 2) and show resources"
    )
    sp.add_argument("name")
    sp.set_defaults(func=cmd_load)

    sp = sub.add_parser("run", help="execute a skill's entry script")
    sp.add_argument("name")
    sp.add_argument("--dry", action="store_true", help="print plan only, no execution")
    sp.add_argument("--yes", action="store_true", help="approve script execution")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser(
        "context", help="assemble skill context for an agent (Level 2+3)"
    )
    sp.add_argument("name")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--no-refs", action="store_true", help="do not load references")
    sp.set_defaults(func=cmd_context)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
