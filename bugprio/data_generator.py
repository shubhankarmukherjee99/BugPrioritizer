"""
Generates a synthetic *historical bug-tracker* dataset used to train the
ML priority classifier. Each row mimics a triaged bug report:
    title, description, component, exception_type, priority (P1..P4)

In a real deployment you would replace data/historical_bugs.csv with an
export from Jira / GitHub Issues / Bugzilla containing the same columns.
"""
import csv
import random

TEMPLATES = {
    "P1": [
        ("Security: {comp} allows login with empty password", "authentication bypass, unauthorized access to accounts", "AssertionError"),
        ("Account takeover via duplicate registration in {comp}", "existing user credentials overwritten, security vulnerability", "MissingExceptionHandling"),
        ("Customers overcharged at checkout in {comp}", "payment total wrong, money lost, billing incorrect", "AssertionError"),
        ("Data loss when saving records in {comp}", "database corruption, records deleted permanently", "IOError"),
        ("Application crash on startup in {comp}", "service down for all users, production outage", "RuntimeError"),
        ("SQL injection possible in {comp} search", "security hole, attacker can read database", "AssertionError"),
        ("Password stored in plain text by {comp}", "credentials leak, security compliance failure", "AssertionError"),
        ("Negative stock allowed in {comp}", "inventory goes negative, orders shipped without stock, money lost", "MissingExceptionHandling"),
    ],
    "P2": [
        ("Unhandled ZeroDivisionError in {comp}", "crash when input is zero, unhandled exception reaches user", "ZeroDivisionError"),
        ("KeyError crash for unknown item in {comp}", "unhandled exception, request fails with 500 error", "KeyError"),
        ("TypeError when field is missing in {comp}", "crash on malformed input, feature unusable", "TypeError"),
        ("Wrong calculation result in {comp}", "incorrect output, users get wrong numbers", "AssertionError"),
        ("Report export fails in {comp}", "feature broken for many users, workaround exists", "ValueError"),
        ("Session not expired in {comp}", "token remains valid after logout", "AssertionError"),
        ("Empty list crashes {comp}", "ZeroDivisionError on empty input, crash", "ZeroDivisionError"),
    ],
    "P3": [
        ("Rounding precision issue in {comp}", "integer division loses decimals, minor inaccuracy", "AssertionError"),
        ("Slow response in {comp} under load", "performance degradation, timeout sometimes", "TimeoutError"),
        ("Intermittent network timeout in {comp}", "flaky external service, retry succeeds", "TimeoutError"),
        ("Validation message unclear in {comp}", "error message confusing, wrong error type raised", "ValueError"),
        ("Edge case not handled in {comp}", "unusual input gives unexpected but harmless result", "AssertionError"),
        ("Deprecated API warning in {comp}", "warning logged, works for now", "DeprecationWarning"),
    ],
    "P4": [
        ("Typo in {comp} log message", "cosmetic spelling mistake in logs", "AssertionError"),
        ("Inconsistent formatting in {comp} output", "cosmetic alignment issue, no functional impact", "AssertionError"),
        ("Docstring outdated in {comp}", "documentation mismatch, cosmetic", "AssertionError"),
        ("Minor UI label misaligned in {comp}", "cosmetic layout issue", "AssertionError"),
        ("Unused variable warning in {comp}", "code style, lint warning only", "SyntaxWarning"),
    ],
}

COMPONENTS = {
    "P1": ["auth", "login", "payment", "checkout", "billing", "database", "security", "inventory"],
    "P2": ["calculator", "inventory", "orders", "reports", "api", "cart", "auth"],
    "P3": ["calculator", "reports", "search", "api", "exchange", "utils"],
    "P4": ["ui", "logging", "docs", "utils", "reports"],
}

NOISE = ["reported by QA", "seen in staging", "customer ticket", "regression from last release",
         "found in nightly build", "reproducible", "found during code review", ""]


def generate(path, n=800, seed=42):
    rng = random.Random(seed)
    weights = {"P1": 0.2, "P2": 0.3, "P3": 0.3, "P4": 0.2}
    rows = []
    for _ in range(n):
        p = rng.choices(list(weights), weights=list(weights.values()))[0]
        title, desc, exc = rng.choice(TEMPLATES[p])
        comp = rng.choice(COMPONENTS[p])
        # 8% label noise to keep the model honest
        label = p if rng.random() > 0.08 else rng.choice(list(weights))
        rows.append({
            "title": title.format(comp=comp),
            "description": f"{desc}; {rng.choice(NOISE)}".strip("; "),
            "component": comp,
            "exception_type": exc,
            "priority": label,
        })
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return len(rows)
