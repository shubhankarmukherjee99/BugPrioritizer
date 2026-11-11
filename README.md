# Automated Software Testing & Bug Prioritization Tool (Python)

A command-line tool that **automatically runs a project's test suite, turns test failures into
de-duplicated bug reports, and ranks them by priority (P1 Critical → P4 Low)** using a hybrid
of an explainable rule-based risk score and a machine-learning classifier trained on historical bugs.

## Features
| Module | What it does |
|---|---|
| `test_runner.py` + `pytest_plugin.py` | Runs pytest in an isolated subprocess, captures outcome, duration, exception type and full traceback frames; **re-runs failures** to detect **flaky tests** |
| `static_analysis.py` | Uses Python `ast` to compute **cyclomatic complexity** and LOC of every function |
| `bug_extractor.py` | Locates the faulty source function from the traceback (or from what the test calls) and **groups failures into unique bugs** |
| `prioritizer.py` | **Hybrid scoring**: rule-based risk (60%) + ML severity (40%) → P1–P4, with human-readable reasons |
| `data_generator.py` | Builds a synthetic historical bug-tracker dataset for training |
| `report.py` | Produces an **HTML dashboard**, **CSV** and **JSON** report |

## Prioritization model
```
rule_score  = 0.25·exception_severity + 0.25·component_criticality
            + 0.15·impact(#failing tests) + 0.10·complexity + 0.25·critical_keywords
ml_score    = Σ P(class) × weight(class)     weights: P1=1.0, P2=0.7, P3=0.4, P4=0.1
final_score = 0.6·rule_score + 0.4·ml_score   (× 0.6 if the bug is flaky)

final ≥ 0.70 → P1 Critical | ≥ 0.50 → P2 High | ≥ 0.30 → P3 Medium | else P4 Low
```
ML model: TF-IDF (unigrams + bigrams) → Logistic Regression, ~90% hold-out accuracy on the synthetic data.

## Project structure
```
BugPrioritizer/
├── main.py                 # CLI entry point
├── requirements.txt
├── bugprio/                # the tool
├── sample_app/             # demo app with deliberate bugs (auth, inventory, calculator)
│   └── tests/              # its pytest suite (19 tests)
├── tests/                  # unit tests for the tool itself
├── data/                   # historical_bugs.csv + trained model (generated)
└── reports/                # bug_report.html / .csv / .json (generated)
```

## How to run
```bash
pip install -r requirements.txt
python main.py train                                     # generate data + train model
python main.py run --project . --tests sample_app/tests  # test + prioritize
# open reports/bug_report.html in a browser
```
Options: `--reruns 5` (flaky detection), `--out <dir>`, `--fail-on P1` (non-zero exit for CI pipelines).

Test **any** Python project:
```bash
python main.py run --project /path/to/project --tests /path/to/project/tests
```
Run the tool's own unit tests: `python -m pytest tests`

## Sample output
```
#  ID       PRIORITY      SCORE  BUG                                           LOCATION
1  BUG-001  P1 Critical   0.75   AssertionError in auth.login()                auth.py:21
2  BUG-002  P1 Critical   0.71   MissingExceptionHandling in auth.register()   auth.py:11
3  BUG-007  P1 Critical   0.71   MissingExceptionHandling in inventory.remove  inventory.py:17
4  BUG-008  P2 High       0.70   AssertionError in inventory.apply_discount()  inventory.py:25
5  BUG-006  P2 High       0.59   KeyError in inventory.remove_item()           inventory.py:19
6  BUG-003  P2 High       0.50   ZeroDivisionError in calculator.divide()      calculator.py:14
7  BUG-005  P3 Medium     0.49   ZeroDivisionError in calculator.average()     calculator.py:19
8  BUG-004  P3 Medium     0.44   AssertionError in calculator.average()        calculator.py:17
9  BUG-009  P3 Medium *   0.31   TimeoutError in inventory.fetch_exchange_rat  inventory.py:41
* = flaky
```
`fetch_exchange_rate()` fails randomly 50% of the time to demonstrate flaky-test detection, so it
appears only on runs where its first attempt fails.

## Using real data
Replace `data/historical_bugs.csv` with an export from Jira / GitHub Issues / Bugzilla that has the
columns `title, description, component, exception_type, priority` and run `python main.py train`.
Tune `COMPONENT_CRITICALITY` and `CRITICAL_KEYWORDS` in `bugprio/prioritizer.py` for your domain.

## Possible extensions
Code-coverage weighting (`coverage.py`), git-blame churn metrics, GitHub Issues auto-filing,
a Streamlit dashboard, and BERT embeddings instead of TF-IDF.
