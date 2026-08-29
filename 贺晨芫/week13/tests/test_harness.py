"""Self-contained tests for the progressive skill harness.

No third-party dependencies (no pytest required). Run directly:

    python tests/test_harness.py
"""

from __future__ import annotations

from pathlib import Path

from harness.discovery import SkillIndex
from harness.router import route, best
from harness.loader import ProgressiveLoader
from harness.executor import DryRunExecutor, ScriptExecutor, ContextExecutor

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _index() -> SkillIndex:
    return SkillIndex.discover([EXAMPLES])


def test_discovery_finds_example():
    assert "hello-skill" in _index().names()


def test_level1_metadata_is_cheap():
    idx = _index()
    meta = idx.get("hello-skill")
    assert meta is not None
    assert "演示" in meta.description
    # L1: only metadata; body must NOT be loaded into a Skill yet.
    loader = ProgressiveLoader(idx)
    assert loader.state("hello-skill").level == 1


def test_routing_ranks_example():
    idx = _index()
    matches = route("演示 harness 测试", idx, top_k=1)
    assert matches, "expected at least one route match"
    assert matches[0].metadata.name == "hello-skill"


def test_best_returns_none_below_threshold():
    idx = _index()
    assert best("zzzqwkj random gibberish", idx, threshold=0.5) is None


def test_progressive_l2_then_l3():
    idx = _index()
    loader = ProgressiveLoader(idx)
    skill = loader.select("hello-skill")  # L2
    assert loader.state("hello-skill").level == 2

    refs = skill.resources("reference")
    assert refs, "expected a reference resource"
    text = loader.load_reference(skill, refs[0].name)  # L3
    assert "Level 3" in text
    assert loader.state("hello-skill").level == 3
    assert refs[0].name in loader.state("hello-skill").loaded_references


def test_dry_run_plan():
    idx = _index()
    loader = ProgressiveLoader(idx)
    skill = loader.select("hello-skill")
    plan = DryRunExecutor().execute(skill)
    assert "hello-skill" in plan
    assert "scripts/greet.py" in plan


def test_script_execution():
    idx = _index()
    loader = ProgressiveLoader(idx)
    skill = loader.select("hello-skill")
    proc = ScriptExecutor(default_approve=True).execute(skill)
    assert proc.returncode == 0
    assert "Hello," in proc.stdout


def test_script_execution_requires_approval():
    idx = _index()
    loader = ProgressiveLoader(idx)
    skill = loader.select("hello-skill")
    try:
        ScriptExecutor().execute(skill)  # no approval
    except PermissionError:
        return
    raise AssertionError("expected PermissionError without approval")


def test_context_executor_loads_references():
    idx = _index()
    loader = ProgressiveLoader(idx)
    skill = loader.select("hello-skill")
    ctx = ContextExecutor(load_references=True).execute(skill)
    assert ctx["name"] == "hello-skill"
    assert any("detail.md" in k for k in ctx["references"])


def test_douyin_integration_if_present():
    """Wire-up check for the real douyin-keyword-scraper skill (skipped if absent)."""
    user_skills = Path.home() / ".workbuddy" / "skills"
    skill_md = user_skills / "douyin-keyword-scraper" / "SKILL.md"
    if not skill_md.is_file():
        return
    idx = SkillIndex.discover([user_skills])
    loader = ProgressiveLoader(idx)
    skill = loader.select("douyin-keyword-scraper")
    # Root-level scraper.py must be resolved as the entry, not a scripts/ file.
    assert skill.entry_script() == "scraper.py", skill.entry_script()
    # Interpreter should resolve to the system python referenced in the body.
    assert skill.interpreter and "python" in skill.interpreter, skill.interpreter
    plan = DryRunExecutor().execute(skill)
    assert "scraper.py" in plan


def _run_all() -> int:
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for f in funcs:
        try:
            f()
            print(f"PASS  {f.__name__}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  {f.__name__}: {e}")
    print(f"\n{passed}/{len(funcs)} passed")
    return 0 if passed == len(funcs) else 1


if __name__ == "__main__":
    raise SystemExit(_run_all())
