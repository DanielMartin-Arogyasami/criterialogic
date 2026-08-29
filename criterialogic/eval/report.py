"""Render result dicts (from eval.runner) into a compact Markdown report."""
from __future__ import annotations


def _fmt(x, nd=3):
    return f"{x:.{nd}f}" if isinstance(x, (int, float)) else str(x)
def render_report(results: list[dict]) -> str:
    lines: list[str] = ["# CriteriaLogic — evaluation report", ""]
    for r in results:
        m = r["metrics"]
        name = r["model"].get("name", "model")
        lines.append(f"## Task: {r['task']}  ·  Model: {name}  ·  n={r['n_items']}")
        if r["task"] == "matching":
            lines.append(f"- Overall micro-F1: **{_fmt(m['overall_micro_f1'])}**  ·  "
                         f"macro-F1: **{_fmt(m['overall_macro_f1'])}**")
            lines.append("- Per-criterion micro-F1:")
            for tag, v in m["per_criterion"].items():
                lines.append(f"    - {tag}: {_fmt(v['micro_f1'])}  (n={v['n']})")
        elif r["task"] == "compositional":
            lines.append(f"- Overall accuracy: **{_fmt(m['overall_accuracy'])}**")
            lines.append("- Accuracy by nesting depth:")
            for d, v in m["by_depth"].items():
                lines.append(f"    - depth {d}: {_fmt(v['accuracy'])}  (n={v['n']})")
        else:
            lines.append(f"- Accuracy: **{_fmt(m.get('accuracy'))}**")
        lines.append(f"- ECE: {_fmt(r['calibration']['ece'])}  ·  "
                     f"selective-acc @50% coverage: {_fmt(r['calibration'].get('selective_accuracy_at_50pct_coverage'))}")
        if r["failure_taxonomy"]:
            fb = "  ".join(f"{k}={v}" for k, v in sorted(r["failure_taxonomy"].items()))
            lines.append(f"- Failure taxonomy (errors): {fb}")
        else:
            lines.append("- Failure taxonomy (errors): none")
        lines.append("")
    return "\n".join(lines)
