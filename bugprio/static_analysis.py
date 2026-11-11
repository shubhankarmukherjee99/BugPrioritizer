"""
Static code analysis using Python's `ast` module.

For every function in the source tree we compute:
  * McCabe cyclomatic complexity (1 + number of decision points)
  * lines of code
These metrics feed the risk score: complex code is more likely to hide
further defects and is costlier to fix.
"""
import ast
from pathlib import Path

_DECISION_NODES = (ast.If, ast.For, ast.While, ast.IfExp, ast.ExceptHandler,
                   ast.With, ast.Assert, ast.comprehension, ast.AsyncFor, ast.AsyncWith)


def cyclomatic_complexity(func_node):
    cc = 1
    for node in ast.walk(func_node):
        if isinstance(node, _DECISION_NODES):
            cc += 1
        elif isinstance(node, ast.BoolOp):
            cc += len(node.values) - 1
    return cc


def analyze_source(project_root, exclude=("tests", "test", ".venv", "venv", "__pycache__")):
    """Return {(abs_file_path, function_name): {...metrics...}}."""
    metrics = {}
    tool_pkg = Path(__file__).resolve().parent
    for path in Path(project_root).resolve().rglob("*.py"):
        if tool_pkg in path.parents or path.name == "main.py" and (path.parent / "bugprio").is_dir():
            continue
        if any(part in exclude for part in path.parts) or path.name.startswith("test_"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                loc = (node.end_lineno or node.lineno) - node.lineno + 1
                metrics[(str(path), node.name)] = {
                    "file": str(path),
                    "module": path.stem,
                    "function": node.name,
                    "complexity": cyclomatic_complexity(node),
                    "loc": loc,
                    "start": node.lineno,
                    "end": node.end_lineno or node.lineno,
                }
    return metrics


def find_function_at(metrics, file_path, lineno):
    """Find the innermost function that contains file:lineno."""
    best = None
    for m in metrics.values():
        if m["file"] == str(file_path) and m["start"] <= lineno <= m["end"]:
            if best is None or m["start"] >= best["start"]:
                best = m
    return best


def functions_called_in_test(test_file, test_name, metrics):
    """Names of source functions/methods called inside a test function."""
    try:
        tree = ast.parse(Path(test_file).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return []
    known = {m["function"] for m in metrics.values()}
    base_name = test_name.split("[")[0]
    called = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == base_name:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    f = sub.func
                    name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
                    if name in known and name not in called:
                        called.append(name)
    return called
