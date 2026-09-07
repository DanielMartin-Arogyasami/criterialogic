"""Render result dicts from eval.runner into a compact Markdown report.

The report leads with the caveats that decide whether a number means anything —
degenerate confidence, unanswerable items, a single dominating rationale — because a
table that hides them reads as a finding.
"""
from __future__ import annotations


def _fmt(x, nd=3):
    return f"{x:.{nd}f}" if isinstance(x, (int, float)) and not isinstance(x, bool) else str(x)


def _ci(pair) -> str:
    if not pair or pair[0] is None:
        return ""
    return f" [{_fmt(pair[0])}, {_fmt(pair[1])}]"


def render_report(results: list[dict]) -> str:
    lines: list[str] = ["# CriteriaLogic — evaluation report", ""]
    for r in results:
        m = r["metrics"]
        name = r["model"].get("name", "model")
        lines.append(f"## {r['task']}  ·  {name}  ·  n={r['n_items']}")

        if r["task"] == "compositional":
            lines.append(f"- Accuracy: **{_fmt(m['overall_accuracy'])}**"
                         f"{_ci(m.get('overall_wilson_95'))}")
            lines.append("- By nesting depth:")
            for d, v in m["by_depth"].items():
                lines.append(f"    - depth {d}: {_fmt(v['accuracy'])}{_ci(v.get('wilson_95'))}"
                             f"  (n={v['n']})")
            trend = m.get("trend")
            if trend:
                sp = trend["spearman"]
                lines.append(f"- Depth trend: rho={_fmt(sp['rho'])}, "
                             f"p={_fmt(sp['p_one_sided'])} ({sp['mode']}, "
                             f"floor {_fmt(sp['min_attainable_p'])}); "
                             f"monotonic={trend['monotonic_non_increasing']}")
                unresolved = [(p["depths"], p["n_per_depth_needed"])
                              for p in trend["pairwise"] if p["cis_overlap"]]
                if unresolved:
                    # -1 is the sentinel for "no difference to size", which must not be
                    # printed as a sample-size requirement of minus one.
                    detail = ", ".join(
                        f"{d}: identical" if n == -1 else f"{d}: n>={n}"
                        for d, n in unresolved)
                    lines.append(f"    - indistinguishable at this n — {detail}")
        elif r["task"] in ("real_criteria", "matching"):
            lines.append(f"- micro-F1: **{_fmt(m['overall_micro_f1'])}**  ·  "
                         f"macro-F1: **{_fmt(m['overall_macro_f1'])}**  ·  "
                         f"accuracy: {_fmt(m['overall_accuracy'])}{_ci(m.get('overall_wilson_95'))}")
            lines.append(f"- Gold met-rate: {_fmt(m['gold_met_rate'])} over "
                         f"{m['n_groups']} source trials")
        else:
            lines.append(f"- Accuracy: **{_fmt(m.get('accuracy'))}**")

        cal = r["calibration"]
        lines.append(f"- ECE: {_fmt(cal['ece'])}  ·  mean confidence: "
                     f"{_fmt(cal['mean_confidence'])}  ·  abstentions: {cal['n_abstain']}")
        if not cal["usable_confidence_signal"]:
            lines.append("    - **no usable confidence signal**: every prediction carries "
                         "the same confidence, so the selective-accuracy curve is flat at "
                         "the overall accuracy and abstention cannot be evaluated.")
        else:
            sa = cal["selective_accuracy"]
            lines.append(f"    - selective accuracy @30%/50%/100% coverage: "
                         f"{sa.get('30%')} / {sa.get('50%')} / {sa.get('100%')}")

        tax = r["failure_taxonomy"]
        if tax["categories"]:
            body = "  ".join(f"{k}={v}" for k, v in tax["categories"].items())
            lines.append(f"- Failure taxonomy (labeller v{tax['labeller_version']}, "
                         f"heuristic): {body}")
        else:
            lines.append("- Failure taxonomy: no scored errors")
        if tax["n_errors_unanswerable"]:
            lines.append(f"    - {tax['n_errors_unanswerable']} of {tax['n_errors']} errors "
                         f"excluded as unanswerable from the prompt (renderer defect, not "
                         f"a reasoning failure)")
        if tax["n_errors"] and tax["distinct_rationales"]:
            lines.append(f"    - {tax['n_errors']} errors span "
                         f"{tax['distinct_rationales']} distinct rationales "
                         f"(largest cluster {tax['largest_rationale_cluster']})")
        prov = r.get("provenance", {})
        if prov:
            lines.append(f"- Provenance: sources={','.join(prov.get('sources', []))}, "
                         f"polarities={','.join(prov.get('polarities', []))}, "
                         f"patients={prov.get('patients')}, "
                         f"composition={prov.get('composition')}")
        lines.append("")
    return "\n".join(lines)
