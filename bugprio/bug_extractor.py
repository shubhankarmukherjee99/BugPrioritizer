"""
Converts raw test failures into de-duplicated bug reports.

Several failing tests often point at the same defect, so failures are grouped
by (module, function, exception type). The location of the bug is taken from
the deepest traceback frame that lies inside the project's source code; if the
failure is a plain assertion inside the test, we fall back to the source
function the test calls.
"""
from dataclasses import dataclass, field

from .static_analysis import find_function_at, functions_called_in_test

# pytest's "DID NOT RAISE" shows up as typename "Failed"
_FRIENDLY_EXC = {"Failed": "MissingExceptionHandling"}


@dataclass
class Bug:
    bug_id: str
    module: str
    function: str
    file: str
    line: int
    exception_type: str
    message: str
    tests: list = field(default_factory=list)
    flaky_tests: list = field(default_factory=list)
    complexity: int = 1
    loc: int = 1
    # filled in by the prioritizer
    rule_score: float = 0.0
    ml_score: float = 0.0
    ml_label: str = ""
    final_score: float = 0.0
    priority: str = ""
    reasons: list = field(default_factory=list)

    @property
    def title(self):
        return f"{self.exception_type} in {self.module}.{self.function}()"

    @property
    def description(self):
        return f"{self.message or ''} | failing tests: {', '.join(t.split('::')[-1] for t in self.tests)}"

    @property
    def is_flaky(self):
        return len(self.flaky_tests) == len(self.tests) and len(self.tests) > 0


def _locate(result, metrics):
    source_files = {m["file"] for m in metrics.values()}
    for fr in reversed(result.frames):
        if fr["path"] in source_files:
            fn = find_function_at(metrics, fr["path"], fr["lineno"])
            if fn:
                return fn, fr["lineno"]
    called = functions_called_in_test(result.test_file, result.test_name, metrics)
    if called:
        target = called[-1]          # function closest to the failing assertion
        for m in metrics.values():
            if m["function"] == target:
                return m, m["start"]
    return None, 0


def extract_bugs(results, metrics):
    groups = {}
    for r in results:
        if not r.is_failure:
            continue
        fn, line = _locate(r, metrics)
        exc = _FRIENDLY_EXC.get(r.exception_type, r.exception_type or "UnknownError")
        if fn:
            key = (fn["module"], fn["function"], exc)
        else:
            key = (r.test_file.split("/")[-1], r.test_name, exc)
        if key not in groups:
            groups[key] = Bug(
                bug_id="", module=key[0], function=key[1],
                file=fn["file"] if fn else r.test_file, line=line,
                exception_type=exc, message=(r.message or "").split("\n")[0][:200],
                complexity=fn["complexity"] if fn else 1, loc=fn["loc"] if fn else 1)
        bug = groups[key]
        bug.tests.append(r.nodeid)
        if r.is_flaky:
            bug.flaky_tests.append(r.nodeid)
    bugs = list(groups.values())
    for i, b in enumerate(bugs, 1):
        b.bug_id = f"BUG-{i:03d}"
    return bugs
