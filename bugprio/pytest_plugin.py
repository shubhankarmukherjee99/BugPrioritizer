"""
Pytest plugin loaded into the test subprocess with `-p bugprio.pytest_plugin`.
It records every test outcome together with the full traceback frames and
writes them to the JSON file named in the BUGPRIO_OUTPUT environment variable.
"""
import json
import os
import time

import pytest

_results = {}


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    rep = yield
    nodeid = item.nodeid
    entry = _results.setdefault(nodeid, {
        "nodeid": nodeid,
        "test_file": str(item.path),
        "test_name": item.name,
        "outcome": "passed",
        "duration": 0.0,
        "exception_type": None,
        "message": None,
        "frames": [],
    })
    entry["duration"] += rep.duration

    if rep.failed and entry["outcome"] != "failed":
        entry["outcome"] = "failed" if rep.when == "call" else "error"
        if call.excinfo is not None:
            entry["exception_type"] = call.excinfo.typename
            entry["message"] = str(call.excinfo.value)[:500]
            entry["frames"] = [
                {"path": str(tb.path), "lineno": tb.lineno + 1, "name": tb.name}
                for tb in call.excinfo.traceback
            ]
    elif rep.skipped and entry["outcome"] == "passed":
        entry["outcome"] = "skipped"
    return rep


def pytest_sessionfinish(session, exitstatus):
    out = os.environ.get("BUGPRIO_OUTPUT")
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"timestamp": time.time(), "results": list(_results.values())}, f, indent=2)
