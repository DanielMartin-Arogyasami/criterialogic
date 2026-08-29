"""Collect every empirical value the CriteriaLogic paper's Section 7 can currently be filled with.

Writes results/paper_data.md (human-readable, keyed to paper sections) and
results/paper_data.json (machine-readable). Reports explicitly what CANNOT be filled.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from criterialogic import __version__ as pkg_version
from criterialogic.data.harmonize import harmonized_n2c2_criteria
from criterialogic.data.synthetic import _collect_atoms, generate_matching_items
from criterialogic.eval.runner import run_task
from criterialogic.metrics.calibration import selective_accuracy_curve
from criterialogic.models import NegationBlindModel, RuleBasedModel
from criterialogic.models.llm_api import OpenAILLMModel
from criterialogic.schema.logical_form import SCHEMA_VERSION
from criterialogic.tasks.base import expression_depth
from criterialogic.tasks.compositional import _atom_pool, generate_compositional_items
from criterialogic.taxonomy.categories import CATEGORY_DESCRIPTIONS

RESULTS = Path("results")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
COVERAGES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def curve_at(items, preds):
    """Selective accuracy sampled at fixed coverage levels."""
    curve = selective_accuracy_curve(items, preds)
    out = {}
    for c in COVERAGES:
        pt = next((p for p in curve if p["coverage"] >= c - 1e-9), None)
        out[f"{int(c * 100)}%"] = round(pt["accuracy"], 4) if pt else None
    return out


def run_pytest() -> dict:
    """Actually run the suite. A hardcoded count in a reproducibility block goes stale."""
    p = subprocess.run([sys.executable, "-m", "pytest", "--tb=no", "-q"],
                       capture_output=True, text=True, timeout=1800)
    tail = [ln for ln in p.stdout.strip().splitlines() if ln.strip()]
    summary = tail[-1] if tail else ""
    m = re.search(r"(\d+) passed", summary)
    fail = re.search(r"(\d+) failed", summary)
    return {"passed": int(m.group(1)) if m else None,
            "failed": int(fail.group(1)) if fail else 0,
            "exit_code": p.returncode, "summary": summary}


def run_ruff() -> dict:
    p = subprocess.run([sys.executable, "-m", "ruff", "check", ".", "--no-cache"],
                       capture_output=True, text=True, timeout=600,
                       env={**os.environ, "NO_COLOR": "1"})
    out = _ANSI_RE.sub("", p.stdout.strip() or p.stderr.strip())
    return {"exit_code": p.returncode,
            "summary": out.splitlines()[-1][:200] if out else ""}


def evaluate(model, items, seed):
    preds = model.predict_batch(items)
    res = run_task(model, items, seed=seed)
    res["selective_accuracy"] = curve_at(items, preds)
    res["n_abstain"] = sum(1 for p in preds if p.abstain)
    res["mean_confidence"] = round(sum(p.confidence for p in preds) / len(preds), 4)
    return res, preds


def main() -> None:
    data: dict = {}

    # ---------------- Section 3: dataset composition ---------------- #
    criteria = harmonized_n2c2_criteria()
    match_items = generate_matching_items(criteria, n_per_criterion=8, seed=13)
    comp_items = generate_compositional_items(n_per_depth=12, max_depth=3, seed=29)
    big_items = generate_compositional_items(n_per_depth=100, max_depth=4, seed=29)
    pool = _atom_pool()

    crit_detail = []
    for f in criteria:
        atoms = _collect_atoms(f.expression)
        crit_detail.append({
            "tag": f.metadata.get("tag"),
            "polarity": f.polarity.value,
            "depth": expression_depth(f.expression),
            "n_atoms": len(atoms),
            "has_temporal": any(a.temporal is not None for a in atoms),
            "has_numeric": any(a.numeric is not None for a in atoms),
        })

    data["dataset_composition"] = {
        "schema_version": SCHEMA_VERSION,
        "package_version": pkg_version,
        "n2c2_criteria_encoded": len(criteria),
        "n2c2_criteria_detail": crit_detail,
        "task_c_matching_items": len(match_items),
        "task_c_gold_met_rate": round(sum(i.gold for i in match_items) / len(match_items), 4),
        "task_d_demo_items": len(comp_items),
        "task_d_demo_gold_met_rate": round(sum(i.gold for i in comp_items) / len(comp_items), 4),
        "task_d_demo_depth_distribution": dict(sorted(Counter(i.depth for i in comp_items).items())),
        "task_d_large_items": len(big_items),
        "task_d_large_gold_met_rate": round(sum(i.gold for i in big_items) / len(big_items), 4),
        "task_d_large_depth_distribution": dict(sorted(Counter(i.depth for i in big_items).items())),
        "atom_pool_size": len(pool),
        "atom_pool_source": "atoms extracted from verbatim ClinicalTrials.gov eligibility text",
        "seeds": {"matching": 13, "compositional": 29, "large_compositional": 29},
    }

    # ---------------- Section 7: runs ---------------- #
    runs: dict = {}

    for mname, ctor in [("rule_based", RuleBasedModel), ("negation_blind", NegationBlindModel)]:
        r, _ = evaluate(ctor(), match_items, 13)
        runs[f"matching::{mname}"] = r
        r, _ = evaluate(ctor(), comp_items, 29)
        runs[f"compositional::{mname}"] = r
        r, _ = evaluate(ctor(), big_items, 29)
        runs[f"compositional_large::{mname}"] = r

    # OpenAI: served from the on-disk response cache (no new API spend expected).
    llm = OpenAILLMModel()
    for label, items, seed in [("matching", match_items, 13), ("compositional", comp_items, 29)]:
        r, preds = evaluate(llm, items, seed)
        runs[f"{label}::openai"] = r
        runs[f"{label}::openai"]["error_items"] = [
            {
                "item_id": it.item_id,
                "gold": "met" if it.gold else "not_met",
                "predicted": "met" if p.label else "not_met",
                "confidence": p.confidence,
                "category": None,
                "rationale": p.rationale,
            }
            for it, p in zip(items, preds) if p.label != it.gold
        ]

    # attach heuristic categories to the listed error items
    from criterialogic.taxonomy.annotate import categorize_error
    for label, items in [("matching", match_items), ("compositional", comp_items)]:
        preds = {p.item_id: p for p in llm.predict_batch(items)}
        for e in runs[f"{label}::openai"]["error_items"]:
            it = next(i for i in items if i.item_id == e["item_id"])
            e["category"] = categorize_error(it, preds[it.item_id]).value

    data["runs"] = runs

    # ---------------- Section 7.6 validation invariants ---------------- #
    data["reference_implementation_validation"] = {
        "rule_based_matching_micro_f1": runs["matching::rule_based"]["metrics"]["overall_micro_f1"],
        "rule_based_compositional_accuracy": runs["compositional::rule_based"]["metrics"]["overall_accuracy"],
        "rule_based_errors": sum(runs["matching::rule_based"]["failure_taxonomy"].values()),
        "negation_blind_taxonomy_matching": runs["matching::negation_blind"]["failure_taxonomy"],
        "negation_blind_taxonomy_compositional": runs["compositional::negation_blind"]["failure_taxonomy"],
        "negation_blind_depth_curve_large": {
            str(d): v["accuracy"]
            for d, v in runs["compositional_large::negation_blind"]["metrics"]["by_depth"].items()
        },
        "interpretation": (
            "Rule-based == oracle on already-structured forms, so its perfect scores are a "
            "software-validation artifact, NOT an empirical finding."
        ),
    }

    # ---------------- Taxonomy codebook ---------------- #
    data["taxonomy_codebook"] = {c.value: d for c, d in CATEGORY_DESCRIPTIONS.items()}

    # ---------------- Reproducibility ---------------- #
    try:
        freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                                capture_output=True, text=True, timeout=120).stdout.split()
    except Exception:
        freeze = []
    data["reproducibility"] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "llm_model_id": llm.model,
        "llm_temperature_requested": 0.0,
        "llm_temperature_effective": "none (API default)",
        "llm_temperature_note": (
            "gpt-5-nano rejects a custom temperature; the adapter drops it and retries, so every "
            "completion used the API default. The dropped parameter is not recorded per call — "
            "see results/DISCREPANCIES.md entry 3."
        ),
        "llm_response_cache_entries": len(list(Path(".criterialogic_cache").glob("*.json"))),
        "packages": [p for p in freeze if p.split("==")[0].lower() in
                     {"pydantic", "pydantic-core", "openai", "pytest", "ruff", "criterialogic"}],
        "tests": run_pytest(),
        "lint": run_ruff(),
    }

    # ---------------- What cannot be filled ---------------- #
    data["cannot_fill"] = {
        "7.1 Task A (structuring)": "Chia corpus not downloaded and no structuring model implemented "
                                    "(entity F1 / relation F1 / exact match unavailable).",
        "7.1 Task B (typing & polarity)": "Requires Chia-derived labels and a classification model; "
                                          "tasks/typing_polarity.py is a task-name contract only.",
        "7.1 Task C on REAL patients": "n2c2 2018 records are DUA-gated and absent; all Task C numbers "
                                       "here use synthetic patients over the real public criterion definitions.",
        "6. Encoder baselines": "models/encoder.py raises NotImplementedError; needs transformers/torch "
                                "plus a fine-tuned checkpoint (BioClinicalBERT / PubMedBERT / BioBERT).",
        "6. Open-weight LLMs": "models/llm_local.py is a stub; needs an HF/vLLM runtime.",
        "6. Additional API LLMs": "The available API project grants access to gpt-5-nano only; "
                                  "GPT-4-class and Claude-class models returned 403 model_not_found.",
        "7.5 Ablations": "No prompt-design, few-shot-count, or retrieval ablation has been run; "
                         "the toolkit ships a single fixed zero-shot prompt.",
        "5. Human-vs-automatic kappa": "Requires the domain expert to fill human_category in "
                                       "results/errors_openai_*.csv, then run taxonomy.reliability.",
        "5. Test-retest kappa": "Requires a second annotation pass after a washout interval.",
    }

    data["discrepancies"] = [
        {
            "location": "Paper Sec. 3.4 vs criterialogic/tasks/compositional.py::_atom_pool",
            "status": "resolved-in-code; Sec. 3.4 wording still needs an author decision",
            "paper_says": "Task D atoms are 'extracted from real ClinicalTrials.gov criteria'.",
            "code_does": "Atoms are now extracted from verbatim ClinicalTrials.gov v2 eligibility "
                         "text into data/ctgov_atom_pool.json, each carrying its source NCT ID, "
                         "source sentence, and the trial's first-posted date. The generator raises "
                         "if the pool is absent instead of falling back to the n2c2 leaves.",
            "action": "See results/DISCREPANCIES.md entry 1 for the four qualifications the Sec. 3.4 "
                      "wording must respect (synthetic nesting, conservative extraction yield, "
                      "polarity-free predicates, dated contamination claim).",
        },
        {
            "location": "Paper Sec. 7.2 hypothesis",
            "paper_says": "Accuracy declines monotonically with nesting depth.",
            "data_shows": "See 7.2 table: not monotonic for every system at these sample sizes.",
            "action": "State the observed pattern; do not assert monotonicity without wider n.",
        },
    ]

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "paper_data.json").write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    write_markdown(data)
    print(f"[wrote] {RESULTS / 'paper_data.json'}")
    print(f"[wrote] {RESULTS / 'paper_data.md'}")


def f3(x):
    return f"{x:.3f}" if isinstance(x, (int, float)) else "n/a"


def write_markdown(d: dict) -> None:
    r = d["runs"]
    L: list[str] = []
    A = L.append

    A("# CriteriaLogic — collected data for the paper")
    A("")
    A(f"Generated {d['reproducibility']['timestamp_utc']} · package v{d['dataset_composition']['package_version']} "
      f"· schema v{d['dataset_composition']['schema_version']} · Python {d['reproducibility']['python']}")
    A("")
    A("> **INTEGRITY BANNER — read before using any number below.**")
    A("> Task C here uses the *real, public* n2c2 criterion definitions paired with **synthetic patients**, "
      "not the DUA-gated n2c2 records. Task D is **synthetic by construction**. The `rule_based` baseline "
      "evaluates an already-structured logical form and is therefore *the oracle itself*: its perfect scores "
      "are a software-validation artifact (paper §7.6), **not** an empirical finding. Only the `openai` rows "
      "are genuine model measurements, and even those are measured against synthetic patients.")
    A("")

    # ---- Section 3 ---- #
    c = d["dataset_composition"]
    A("## §3 Dataset composition (verified from code, not placeholders)")
    A("")
    A(f"- n2c2 criteria encoded as LogicalForms: **{c['n2c2_criteria_encoded']}** (all 13 official tags)")
    A(f"- Task C items: **{c['task_c_matching_items']}** (13 criteria × 8 synthetic patients, seed {c['seeds']['matching']}); "
      f"gold met-rate {c['task_c_gold_met_rate']}")
    A(f"- Task D demo set: **{c['task_d_demo_items']}** items, depths "
      f"{c['task_d_demo_depth_distribution']}, seed {c['seeds']['compositional']}; gold met-rate {c['task_d_demo_gold_met_rate']}")
    A(f"- Task D large set: **{c['task_d_large_items']}** items, depths "
      f"{c['task_d_large_depth_distribution']}; gold met-rate {c['task_d_large_gold_met_rate']}")
    A(f"- Atom pool for Task D: **{c['atom_pool_size']}** distinct atoms — {c['atom_pool_source']}")
    A("")
    A("### Per-criterion structural profile (feeds §3.2 and S2)")
    A("")
    A("| Tag | Polarity | Nesting depth | Atoms | Temporal | Numeric |")
    A("|---|---|---|---|---|---|")
    for x in c["n2c2_criteria_detail"]:
        A(f"| {x['tag']} | {x['polarity']} | {x['depth']} | {x['n_atoms']} | "
          f"{'yes' if x['has_temporal'] else 'no'} | {'yes' if x['has_numeric'] else 'no'} |")
    A("")

    # ---- 7.1 ---- #
    A("## §7.1 Main leaderboard (rows that can be filled today)")
    A("")
    A("| Task | System | Headline metric | Value | ECE | n |")
    A("|---|---|---|---|---|---|")
    for key, label, metric in [
        ("matching::rule_based", "rule_based (= oracle)", "micro-F1"),
        ("matching::negation_blind", "negation_blind (illustrative)", "micro-F1"),
        ("matching::openai", "gpt-5-nano", "micro-F1"),
    ]:
        x = r[key]
        A(f"| C matching | {label} | {metric} | **{f3(x['metrics']['overall_micro_f1'])}** "
          f"(macro {f3(x['metrics']['overall_macro_f1'])}) | {f3(x['calibration']['ece'])} | {x['n_items']} |")
    for key, label in [
        ("compositional::rule_based", "rule_based (= oracle)"),
        ("compositional::negation_blind", "negation_blind (illustrative)"),
        ("compositional::openai", "gpt-5-nano"),
    ]:
        x = r[key]
        A(f"| D compositional | {label} | accuracy | **{f3(x['metrics']['overall_accuracy'])}** | "
          f"{f3(x['calibration']['ece'])} | {x['n_items']} |")
    for key, label in [
        ("compositional_large::rule_based", "rule_based (= oracle)"),
        ("compositional_large::negation_blind", "negation_blind (illustrative)"),
    ]:
        x = r[key]
        A(f"| D compositional (400-item) | {label} | accuracy | **{f3(x['metrics']['overall_accuracy'])}** | "
          f"{f3(x['calibration']['ece'])} | {x['n_items']} |")
    A("")
    A("Tasks A and B have no rows: see *Cannot fill* below.")
    A("")

    # ---- 7.2 ---- #
    A("## §7.2 Accuracy versus logical nesting depth")
    A("")
    A("| System | Set | d=1 | d=2 | d=3 | d=4 | Δ(shallowest→deepest) |")
    A("|---|---|---|---|---|---|---|")
    for key, label, setname in [
        ("compositional::rule_based", "rule_based", "36-item"),
        ("compositional::negation_blind", "negation_blind", "36-item"),
        ("compositional::openai", "gpt-5-nano", "36-item"),
        ("compositional_large::rule_based", "rule_based", "400-item"),
        ("compositional_large::negation_blind", "negation_blind", "400-item"),
    ]:
        bd = r[key]["metrics"]["by_depth"]
        cells = []
        for dep in ("1", "2", "3", "4"):
            v = bd.get(dep) or bd.get(int(dep))
            cells.append(f"{v['accuracy']:.3f} (n={v['n']})" if v else "—")
        vals = [(bd.get(x) or bd.get(int(x))) for x in ("1", "2", "3", "4")]
        vals = [v for v in vals if v]
        delta = f"{vals[-1]['accuracy'] - vals[0]['accuracy']:+.3f}" if len(vals) > 1 else "—"
        A(f"| {label} | {setname} | " + " | ".join(cells) + f" | {delta} |")
    A("")
    A("The 400-item set is the one to cite for the depth claim; the 36-item set is too small "
      "(12 per depth) to resolve a monotonic trend.")
    A("")

    # ---- 7.3 ---- #
    A("## §7.3 Failure-taxonomy breakdown per system")
    A("")
    A("| Task | System | Total errors | Category counts |")
    A("|---|---|---|---|")
    for key in ["matching::rule_based", "matching::negation_blind", "matching::openai",
                "compositional::rule_based", "compositional::negation_blind", "compositional::openai",
                "compositional_large::rule_based", "compositional_large::negation_blind"]:
        x = r[key]
        tax = x["failure_taxonomy"]
        task, model = key.split("::")
        total = sum(tax.values())
        detail = ", ".join(f"{k}={v}" for k, v in sorted(tax.items())) if tax else "none"
        A(f"| {task} | {model} | {total} | {detail} |")
    A("")
    A("### Every gpt-5-nano error, itemized (feeds §7.3 and the S2 error appendix)")
    A("")
    A("| Item | Task | Gold | Predicted | Conf. | Heuristic category |")
    A("|---|---|---|---|---|---|")
    for label in ("matching", "compositional"):
        for e in r[f"{label}::openai"]["error_items"]:
            A(f"| `{e['item_id']}` | {label} | {e['gold']} | {e['predicted']} | "
              f"{e['confidence']:.2f} | {e['category']} |")
    A("")

    # ---- 7.4 ---- #
    A("## §7.4 Calibration and abstention")
    A("")
    A("| Task | System | ECE | Mean conf. | Abstentions | " + " | ".join(f"acc@{k}" for k in
      r["matching::rule_based"]["selective_accuracy"]) + " |")
    A("|---|---|---|---|---|" + "---|" * len(r["matching::rule_based"]["selective_accuracy"]))
    for key in ["matching::rule_based", "matching::negation_blind", "matching::openai",
                "compositional::rule_based", "compositional::negation_blind", "compositional::openai"]:
        x = r[key]
        task, model = key.split("::")
        cells = " | ".join(f3(v) for v in x["selective_accuracy"].values())
        A(f"| {task} | {model} | {f3(x['calibration']['ece'])} | {x['mean_confidence']} | "
          f"{x['n_abstain']} | {cells} |")
    A("")

    # ---- 7.6 ---- #
    v = d["reference_implementation_validation"]
    A("## §7.6 Reference-implementation validation (software, not findings)")
    A("")
    A(f"- rule_based Task C micro-F1 = **{f3(v['rule_based_matching_micro_f1'])}**, "
      f"Task D accuracy = **{f3(v['rule_based_compositional_accuracy'])}**, "
      f"total errors = {v['rule_based_errors']} — perfect by construction.")
    A(f"- negation_blind error signature, Task C: {v['negation_blind_taxonomy_matching']}")
    A(f"- negation_blind error signature, Task D: {v['negation_blind_taxonomy_compositional']}")
    A(f"- negation_blind depth curve (400-item): {v['negation_blind_depth_curve_large']}")
    A(f"- {v['interpretation']}")
    A("")

    # ---- taxonomy codebook ---- #
    A("## §5 Taxonomy codebook (as implemented)")
    A("")
    A("| Category | Definition |")
    A("|---|---|")
    for k, desc in d["taxonomy_codebook"].items():
        A(f"| {k} | {desc} |")
    A("")
    A("Annotation inputs are staged at `results/errors_openai_matching.csv` and "
      "`results/errors_openai_compositional.csv`, each with a blank `human_category` column. "
      "Cohen's κ and test–retest agreement remain uncomputed pending the human pass.")
    A("")

    # ---- repro ---- #
    rp = d["reproducibility"]
    A("## §9 Reproducibility metadata")
    A("")
    A(f"- Python {rp['python']} on {rp['platform']}")
    A(f"- LLM: `{rp['llm_model_id']}`, temperature requested {rp['llm_temperature_requested']}, "
      f"effective **{rp['llm_temperature_effective']}** — {rp['llm_temperature_note']}")
    A(f"- Cached LLM responses: {rp['llm_response_cache_entries']}")
    A(f"- Packages: {', '.join(rp['packages'])}")
    A(f"- Tests: {rp['tests']['summary']} · Lint: {rp['lint']['summary']}")
    A(f"- Seeds: {d['dataset_composition']['seeds']}")
    A("")

    # ---- gaps ---- #
    A("## Cannot fill — what the paper still needs")
    A("")
    for k, why in d["cannot_fill"].items():
        A(f"- **{k}** — {why}")
    A("")

    # ---- discrepancies ---- #
    A("## Discrepancies between the paper draft and the implementation")
    A("")
    for i, x in enumerate(d["discrepancies"], 1):
        A(f"{i}. **{x['location']}**")
        A(f"   - Paper: {x.get('paper_says')}")
        A(f"   - Reality: {x.get('code_does') or x.get('data_shows')}")
        A(f"   - Action: {x['action']}")
    A("")

    (RESULTS / "paper_data.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
