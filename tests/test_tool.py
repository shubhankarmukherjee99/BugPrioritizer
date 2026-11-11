"""Unit tests for the tool itself:  python -m pytest tests"""
import ast
from bugprio.static_analysis import cyclomatic_complexity
from bugprio.prioritizer import to_priority, rule_score, PriorityModel
from bugprio.bug_extractor import Bug


def _cc(src):
    return cyclomatic_complexity(ast.parse(src).body[0])


def test_complexity_simple():
    assert _cc("def f():\n    return 1") == 1


def test_complexity_branches():
    assert _cc("def f(x):\n    if x and x > 2:\n        return 1\n    for i in x:\n        pass") == 4


def test_priority_thresholds():
    assert [to_priority(s) for s in (0.9, 0.6, 0.35, 0.1)] == ["P1", "P2", "P3", "P4"]


def _bug(module, exc, msg):
    return Bug("B", module, "f", "x.py", 1, exc, msg, tests=["t::test_x"])


def test_security_bug_outranks_cosmetic():
    sec, _, _ = rule_score(_bug("auth", "PermissionError", "password bypass security"), 1)
    cos, _, _ = rule_score(_bug("ui", "AssertionError", "label misaligned"), 1)
    assert sec > cos


def test_flaky_flag():
    b = _bug("api", "TimeoutError", "timeout")
    b.flaky_tests = list(b.tests)
    assert b.is_flaky


def test_model_trains(tmp_path):
    from bugprio.data_generator import generate
    csv = tmp_path / "h.csv"
    generate(csv, n=300)
    m = PriorityModel()
    assert m.train(csv)["accuracy"] > 0.7
