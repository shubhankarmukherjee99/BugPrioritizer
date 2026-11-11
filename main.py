"""
Automated Software Testing & Bug Prioritization Tool
====================================================

Usage
-----
  python main.py train                                   # build dataset + train ML model
  python main.py run --project . --tests sample_app/tests  # test, detect & prioritize bugs
  python main.py run --project /path/to/proj --tests /path/to/proj/tests --reruns 5
"""
import argparse
import sys
from pathlib import Path

from bugprio.bug_extractor import extract_bugs
from bugprio.data_generator import generate
from bugprio.prioritizer import PRIORITY_NAME, PriorityModel, prioritize
from bugprio.report import write_reports
from bugprio.static_analysis import analyze_source
from bugprio.test_runner import run_tests, summarize

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "historical_bugs.csv"
MODEL = ROOT / "data" / "priority_model.pkl"


def cmd_train(args):
    DATA.parent.mkdir(exist_ok=True)
    n = generate(DATA, n=args.samples)
    print(f"[train] Generated {n} historical bug records -> {DATA}")
    model = PriorityModel()
    m = model.train(DATA)
    model.save(MODEL)
    print(f"[train] Train/test = {m['n_train']}/{m['n_test']}  accuracy = {m['accuracy']}")
    print(m["report"])
    print(f"[train] Model saved -> {MODEL}")


def cmd_run(args):
    project = Path(args.project).resolve()
    tests = Path(args.tests).resolve()

    if not MODEL.exists():
        print("[run] No trained model found - training one first.")
        cmd_train(argparse.Namespace(samples=800))
    model = PriorityModel.load(MODEL)

    print(f"[analysis] Static analysis of {project}")
    metrics = analyze_source(project)
    print(f"[analysis] {len(metrics)} functions analysed")

    results = run_tests(project, tests, reruns=args.reruns)
    summary = summarize(results)
    print(f"[runner] {summary['total']} tests | {summary['passed']} passed | "
          f"{summary['failed'] + summary['error']} failed | {summary['flaky']} flaky")

    bugs = prioritize(extract_bugs(results, metrics), model)
    paths = write_reports(bugs, summary, results, model.metrics, args.out)

    print("\n" + "=" * 92)
    print(f"{'#':<3}{'ID':<9}{'PRIORITY':<14}{'SCORE':<7}{'BUG':<46}{'LOCATION'}")
    print("-" * 92)
    for i, b in enumerate(bugs, 1):
        tag = f"{b.priority} {PRIORITY_NAME[b.priority]}" + (" *" if b.is_flaky else "")
        print(f"{i:<3}{b.bug_id:<9}{tag:<14}{b.final_score:<7.2f}{b.title[:44]:<46}{Path(b.file).name}:{b.line}")
    print("=" * 92)
    print("* = flaky (intermittent)\n")
    for k, p in paths.items():
        print(f"[report] {k.upper():<5} -> {p}")
    return 1 if bugs and args.fail_on and any(b.priority <= args.fail_on for b in bugs) else 0


def main():
    ap = argparse.ArgumentParser(description="Automated Software Testing & Bug Prioritization Tool")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("train", help="generate historical data and train the ML model")
    t.add_argument("--samples", type=int, default=800)
    t.set_defaults(func=cmd_train)

    r = sub.add_parser("run", help="run tests, find bugs and prioritize them")
    r.add_argument("--project", default=".", help="root folder of the project under test")
    r.add_argument("--tests", default="sample_app/tests", help="folder or file containing tests")
    r.add_argument("--reruns", type=int, default=3, help="re-runs per failing test for flaky detection")
    r.add_argument("--out", default=str(ROOT / "reports"), help="output folder for reports")
    r.add_argument("--fail-on", choices=["P1", "P2", "P3", "P4"],
                   help="exit code 1 if any bug at this priority or higher (for CI pipelines)")
    r.set_defaults(func=cmd_run)

    args = ap.parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
