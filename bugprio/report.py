"""Generates the prioritized bug report as HTML, CSV and JSON."""
import csv
import html
import json
from datetime import datetime
from pathlib import Path

from .prioritizer import PRIORITY_NAME

COLORS = {"P1": "#c0392b", "P2": "#e67e22", "P3": "#d4ac0d", "P4": "#27ae60"}


def _row(b):
    return {
        "rank": None, "bug_id": b.bug_id, "priority": b.priority,
        "severity": PRIORITY_NAME[b.priority], "final_score": b.final_score,
        "rule_score": b.rule_score, "ml_score": b.ml_score, "ml_label": b.ml_label,
        "title": b.title, "module": b.module, "function": b.function,
        "location": f"{Path(b.file).name}:{b.line}", "exception": b.exception_type,
        "message": b.message, "complexity": b.complexity, "failing_tests": len(b.tests),
        "flaky": b.is_flaky, "tests": " ; ".join(b.tests), "reasons": " ; ".join(b.reasons),
    }


def write_reports(bugs, summary, results, model_metrics, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, b in enumerate(bugs, 1):
        r = _row(b)
        r["rank"] = i
        rows.append(r)

    # CSV
    csv_path = out / "bug_report.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)

    # JSON
    json_path = out / "bug_report.json"
    json_path.write_text(json.dumps({"summary": summary, "model": {k: v for k, v in model_metrics.items() if k != "report"},
                                     "bugs": rows}, indent=2), encoding="utf-8")

    # HTML
    html_path = out / "bug_report.html"
    html_path.write_text(_html(rows, summary, results, model_metrics), encoding="utf-8")
    return {"html": html_path, "csv": csv_path, "json": json_path}


def _html(rows, s, results, mm):
    counts = {p: sum(1 for r in rows if r["priority"] == p) for p in COLORS}
    total_bugs = max(len(rows), 1)
    dist = "".join(
        f'<div class="seg" style="width:{100*counts[p]/total_bugs:.1f}%;background:{COLORS[p]}" '
        f'title="{p}: {counts[p]}">{p} ({counts[p]})</div>' for p in COLORS if counts[p])
    trs = ""
    for r in rows:
        trs += f"""<tr>
<td>{r['rank']}</td><td>{r['bug_id']}</td>
<td><span class="badge" style="background:{COLORS[r['priority']]}">{r['priority']} {r['severity']}</span>{' <span class="flaky">FLAKY</span>' if r['flaky'] else ''}</td>
<td><div class="bar"><div style="width:{r['final_score']*100:.0f}%;background:{COLORS[r['priority']]}"></div></div>{r['final_score']:.2f}</td>
<td>{r['rule_score']:.2f} / {r['ml_score']:.2f} ({r['ml_label']})</td>
<td><b>{html.escape(r['title'])}</b><br><small>{html.escape(r['message'] or '')}</small></td>
<td><code>{html.escape(r['location'])}</code></td>
<td>{r['complexity']}</td><td>{r['failing_tests']}</td>
<td><small>{html.escape(r['reasons'])}</small></td></tr>"""
    test_rows = "".join(
        f"<tr><td><code>{html.escape(t.nodeid)}</code></td><td class='{t.outcome}'>{t.outcome}"
        f"{' (flaky ' + str(t.rerun_passes) + '/' + str(t.rerun_total) + ')' if t.is_flaky else ''}</td>"
        f"<td>{t.duration*1000:.1f} ms</td></tr>" for t in results)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Bug Prioritization Report</title><style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:30px;color:#222;background:#f6f7f9}}
h1{{margin-bottom:4px}} .muted{{color:#666}}
.cards{{display:flex;gap:14px;margin:20px 0;flex-wrap:wrap}}
.card{{background:#fff;padding:14px 20px;border-radius:8px;box-shadow:0 1px 3px #0002;min-width:110px}}
.card .n{{font-size:26px;font-weight:700}}
.dist{{display:flex;height:28px;border-radius:6px;overflow:hidden;margin:10px 0 25px}}
.seg{{color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center}}
table{{border-collapse:collapse;width:100%;background:#fff;box-shadow:0 1px 3px #0002;margin-bottom:30px}}
th,td{{padding:8px 10px;border-bottom:1px solid #eee;text-align:left;vertical-align:top;font-size:14px}}
th{{background:#2c3e50;color:#fff}}
.badge{{color:#fff;padding:3px 8px;border-radius:4px;font-size:12px;white-space:nowrap}}
.flaky{{background:#8e44ad;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px}}
.bar{{width:80px;height:8px;background:#eee;border-radius:4px;margin-bottom:3px}} .bar div{{height:8px;border-radius:4px}}
.passed{{color:#27ae60}} .failed,.error{{color:#c0392b}} .skipped{{color:#999}}
</style></head><body>
<h1>Automated Testing &amp; Bug Prioritization Report</h1>
<div class="muted">Generated {datetime.now():%d %b %Y, %H:%M} &middot; ML model accuracy (hold-out): {mm.get('accuracy','n/a')}</div>
<div class="cards">
<div class="card"><div class="n">{s['total']}</div>Tests run</div>
<div class="card"><div class="n" style="color:#27ae60">{s['passed']}</div>Passed</div>
<div class="card"><div class="n" style="color:#c0392b">{s['failed']+s['error']}</div>Failed</div>
<div class="card"><div class="n" style="color:#8e44ad">{s['flaky']}</div>Flaky</div>
<div class="card"><div class="n">{s['pass_rate']}%</div>Pass rate</div>
<div class="card"><div class="n">{len(rows)}</div>Unique bugs</div>
</div>
<h2>Priority distribution</h2><div class="dist">{dist}</div>
<h2>Prioritized bug list</h2>
<table><tr><th>#</th><th>ID</th><th>Priority</th><th>Score</th><th>Rule / ML</th><th>Bug</th><th>Location</th><th>CC</th><th>Tests</th><th>Why</th></tr>{trs}</table>
<h2>Test execution log</h2>
<table><tr><th>Test</th><th>Outcome</th><th>Duration</th></tr>{test_rows}</table>
</body></html>"""
