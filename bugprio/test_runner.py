"""
Automated test execution.

Runs pytest in an isolated subprocess (so the target project's imports never
leak into the tool), collects structured results, and re-runs failing tests
several times to detect FLAKY tests (tests that sometimes pass).
"""
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class TestResult:
    nodeid: str
    test_file: str
    test_name: str
    outcome: str                 # passed / failed / error / skipped
    duration: float
    exception_type: str = None
    message: str = None
    frames: list = field(default_factory=list)
    rerun_passes: int = 0
    rerun_total: int = 0

    @property
    def is_failure(self):
        return self.outcome in ("failed", "error")

    @property
    def is_flaky(self):
        return self.is_failure and self.rerun_passes > 0


def _run_pytest(project_root, targets):
    """Run pytest on `targets` and return the list of raw result dicts."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_path = tmp.name
    env = os.environ.copy()
    env["BUGPRIO_OUTPUT"] = out_path
    env["PYTHONPATH"] = os.pathsep.join(
        [str(TOOL_ROOT), str(project_root), env.get("PYTHONPATH", "")])
    cmd = [sys.executable, "-m", "pytest", *targets, "-q", "-p", "bugprio.pytest_plugin",
           "-p", "no:cacheprovider", "--no-header", "-rN"]
    subprocess.run(cmd, cwd=project_root, env=env, capture_output=True, text=True)
    try:
        with open(out_path, encoding="utf-8") as f:
            return json.load(f)["results"]
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def run_tests(project_root, tests_path, reruns=3, verbose=True):
    project_root = Path(project_root).resolve()
    tests_path = Path(tests_path).resolve()

    if verbose:
        print(f"[runner] Executing test suite: {tests_path}")
    raw = _run_pytest(project_root, [str(tests_path)])
    results = [TestResult(**r) for r in raw]

    failing = [r for r in results if r.is_failure]
    if failing and reruns > 0:
        if verbose:
            print(f"[runner] {len(failing)} failure(s); re-running each {reruns}x for flakiness")
        by_id = {r.nodeid: r for r in failing}
        for _ in range(reruns):
            for rr in _run_pytest(project_root, list(by_id)):
                if rr["nodeid"] in by_id:
                    by_id[rr["nodeid"]].rerun_total += 1
                    if rr["outcome"] == "passed":
                        by_id[rr["nodeid"]].rerun_passes += 1
    return results


def summarize(results):
    s = {"total": len(results), "passed": 0, "failed": 0, "error": 0, "skipped": 0, "flaky": 0}
    for r in results:
        s[r.outcome] = s.get(r.outcome, 0) + 1
        if r.is_flaky:
            s["flaky"] += 1
    s["pass_rate"] = round(100 * s["passed"] / s["total"], 1) if s["total"] else 0.0
    return s
