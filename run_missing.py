#!/usr/bin/env python3
"""Run the experiments paper_data.json is missing, and persist what the audit needs.

Run from the repo root (same place collect_paper_data.py works from).

    python run_missing.py --dump-suspects      # free, no API calls. Do this first.
    python run_missing.py --depth4             # the missing leaderboard cell
    python run_missing.py --hard               # a Task D that is not saturated
    python run_missing.py --all                # everything
    python run_missing.py --all --yes          # skip the spend confirmation

Everything is written to results/missing/ and nothing overwrites paper_data.json.

Why each mode exists
--------------------
--dump-suspects  Four of the five gpt-5-nano matching errors share one verbatim rationale
                 asserting that the criterion predicate IS present while gold says not met.
                 Those may be generator bugs scored as reasoning failures. This writes the
                 full item, record and criterion for every error so they can be adjudicated
                 before any of them is attributed to the model. No API calls.

--depth4         compositional_large (400 items, depths 1-4) was only ever run against the
                 two synthetic baselines. gpt-5-nano was scored on the 36-item set only, where
                 it got 36/36 and the 95% CI floor is 0.904. Depth 4 is the one untested place
                 the ceiling might break.

--hard           If gpt-5-nano is still at ceiling at depth 4, Task D does not discriminate
                 and cannot support any claim in Sec. 7.2. This sweeps depth 2..6 to find the
                 depth at which accuracy leaves the ceiling, which is the number the task
                 needs to be built around.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("results/missing")
COVERAGES = [0.1 * i for i in range(1, 11)]


# --------------------------------------------------------------------------- #
# generic serialisation: works for pydantic, dataclasses, or plain objects
# --------------------------------------------------------------------------- #

def to_plain(obj, _depth: int = 0):
    """Best-effort JSON-safe view of an arbitrary object, for inspection dumps."""
    if _depth > 6:
        return f"<max depth: {type(obj).__name__}>"
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [to_plain(x, _depth + 1) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_plain(v, _depth + 1) for k, v in obj.items()}
    for meth in ("model_dump", "dict", "_asdict"):
        if hasattr(obj, meth):
            try:
                return to_plain(getattr(obj, meth)(), _depth + 1)
            except Exception:
                pass
    if hasattr(obj, "__dataclass_fields__"):
        import dataclasses
        try:
            return to_plain(dataclasses.asdict(obj), _depth + 1)
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return {k: to_plain(v, _depth + 1) for k, v in vars(obj).items() if not k.startswith("_")}
    if hasattr(obj, "value"):
        return to_plain(obj.value, _depth + 1)
    return str(obj)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / den
    return (max(0.0, c - h), min(1.0, c + h))


def selective_tie_aware(conf: list[float], correct: list[bool]) -> dict:
    """Expected selective accuracy under random tie-breaking, sampled at deciles."""
    n = len(conf)
    if n == 0:
        return {}
    idx = sorted(range(n), key=lambda i: -conf[i])
    groups: list[list[int]] = []
    for i in idx:
        if groups and conf[groups[-1][0]] == conf[i]:
            groups[-1].append(i)
        else:
            groups.append([i])
    pts, done, acc_sum = [], 0, 0.0
    for g in groups:
        gc = sum(1 for i in g if correct[i])
        rate = gc / len(g)
        for j in range(1, len(g) + 1):
            k = done + j
            pts.append((k / n, (acc_sum + j * rate) / k))
        done += len(g)
        acc_sum += gc
    out = {}
    for c in COVERAGES:
        pt = next((p for p in pts if p[0] >= c - 1e-9), None)
        out[f"{int(c * 100)}%"] = round(pt[1], 4) if pt else None
    out["degenerate_single_bin"] = len(groups) == 1
    return out


# --------------------------------------------------------------------------- #
# imports from the package, with a readable failure
# --------------------------------------------------------------------------- #

def load_package():
    try:
        from criterialogic.data.harmonize import harmonized_n2c2_criteria
        from criterialogic.data.synthetic import generate_matching_items
        from criterialogic.eval.runner import run_task
        from criterialogic.models import NegationBlindModel, RuleBasedModel
        from criterialogic.models.llm_api import OpenAILLMModel
        from criterialogic.tasks.compositional import generate_compositional_items
        from criterialogic.taxonomy.annotate import categorize_error
    except ImportError as e:
        sys.exit(
            f"[error] cannot import criterialogic: {e}\n"
            "Run this from the repo root with the package installed "
            "(pip install -e .), the same way collect_paper_data.py runs."
        )
    return dict(
        harmonized_n2c2_criteria=harmonized_n2c2_criteria,
        generate_matching_items=generate_matching_items,
        generate_compositional_items=generate_compositional_items,
        run_task=run_task,
        RuleBasedModel=RuleBasedModel,
        NegationBlindModel=NegationBlindModel,
        OpenAILLMModel=OpenAILLMModel,
        categorize_error=categorize_error,
    )


def cache_size() -> int:
    p = Path(".criterialogic_cache")
    return len(list(p.glob("*.json"))) if p.exists() else 0


# --------------------------------------------------------------------------- #
# evaluation with per-item persistence
# --------------------------------------------------------------------------- #

def evaluate(pkg, model, items, seed: int, label: str) -> dict:
    preds = model.predict_batch(items)
    res = pkg["run_task"](model, items, seed=seed)

    by_id = {p.item_id: p for p in preds}
    per_item, errors = [], []
    for it in items:
        p = by_id.get(it.item_id)
        if p is None:
            continue
        correct = bool(p.label) == bool(it.gold)
        row = {
            "item_id": it.item_id,
            "depth": getattr(it, "depth", None),
            "gold": "met" if it.gold else "not_met",
            "predicted": "met" if p.label else "not_met",
            "confidence": p.confidence,
            "abstain": bool(getattr(p, "abstain", False)),
            "correct": correct,
        }
        per_item.append(row)
        if not correct:
            try:
                cat = pkg["categorize_error"](it, p).value
            except Exception as e:
                cat = f"<categorize_error failed: {e}>"
            errors.append({**row, "heuristic_category": cat,
                           "rationale": getattr(p, "rationale", None)})

    conf = [r["confidence"] for r in per_item]
    corr = [r["correct"] for r in per_item]
    n_correct = sum(corr)
    lo, hi = wilson(n_correct, len(per_item))

    by_depth = {}
    for r in per_item:
        d = r["depth"]
        if d is None:
            continue
        by_depth.setdefault(str(d), []).append(r["correct"])
    depth_stats = {}
    for d, vals in sorted(by_depth.items(), key=lambda x: int(x[0])):
        k, n = sum(vals), len(vals)
        dlo, dhi = wilson(k, n)
        depth_stats[d] = {"accuracy": round(k / n, 4), "n": n,
                          "wilson_95": [round(dlo, 4), round(dhi, 4)]}

    dup = Counter(e.get("rationale") or "" for e in errors)
    return {
        "label": label,
        "n_items": len(per_item),
        "accuracy": round(n_correct / len(per_item), 4) if per_item else None,
        "wilson_95": [round(lo, 4), round(hi, 4)],
        "at_ceiling": n_correct == len(per_item),
        "by_depth": depth_stats,
        "runner_metrics": to_plain(res.get("metrics") if isinstance(res, dict) else res),
        "selective_accuracy_tie_aware": selective_tie_aware(conf, corr),
        "mean_confidence": round(sum(conf) / len(conf), 4) if conf else None,
        "n_abstain": sum(1 for r in per_item if r["abstain"]),
        "raw_error_count": len(errors),
        "distinct_error_rationales": len(dup),
        "failure_taxonomy_raw": dict(Counter(e["heuristic_category"] for e in errors)),
        "per_item_predictions": per_item,
        "error_items": errors,
        "seed": seed,
    }


# --------------------------------------------------------------------------- #
# modes
# --------------------------------------------------------------------------- #

def mode_dump_suspects(pkg) -> None:
    """No API calls. Regenerate the matching items and dump the flagged ones in full."""
    print("[suspects] regenerating matching items (seed 13, 8 per criterion)")
    criteria = pkg["harmonized_n2c2_criteria"]()
    items = pkg["generate_matching_items"](criteria, n_per_criterion=8, seed=13)

    flagged_prefixes = ("match:ASP-FOR-MI", "match:ALCOHOL-ABUSE")
    crit_by_tag = {}
    for f in criteria:
        tag = None
        try:
            tag = f.metadata.get("tag")
        except Exception:
            pass
        if tag:
            crit_by_tag[tag] = f

    dump = []
    for it in items:
        if not str(it.item_id).startswith(flagged_prefixes):
            continue
        tag = str(it.item_id).split(":")[1] if ":" in str(it.item_id) else None
        dump.append({
            "item_id": it.item_id,
            "gold": "met" if it.gold else "not_met",
            "criterion_tag": tag,
            "criterion_logical_form": to_plain(crit_by_tag.get(tag)),
            "item_full": to_plain(it),
        })

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "suspect_items.json").write_text(json.dumps(dump, indent=2), encoding="utf-8")

    L = ["# Suspect item adjudication",
         "",
         "Four of the five gpt-5-nano matching errors carry one verbatim rationale asserting the",
         "criterion predicate IS present while gold says not_met. For each item below decide:",
         "",
         "- **A — item is mislabelled.** The record states the predicate; gold is wrong. Fix the",
         "  generator, rescore, and remove the error from the taxonomy.",
         "- **B — item is underspecified.** The record neither states nor denies the predicate, so",
         "  the item is unanswerable. Remove it from the set; it measures nothing.",
         "- **C — genuine model error.** The record contains the distinguishing evidence and the",
         "  model missed it. Keep it and record the taxonomy category.",
         "",
         "Verdict C is the only one that may be reported as a reasoning failure in Sec. 7.3.",
         ""]
    for d in dump:
        L += [f"## `{d['item_id']}`  (gold: **{d['gold']}**)", "",
              "```json", json.dumps(d["item_full"], indent=2)[:2500], "```", "",
              "Criterion:", "", "```json",
              json.dumps(d["criterion_logical_form"], indent=2)[:1200], "```", "",
              "**Verdict (A / B / C):** ", "", "**Reasoning:** ", "", "---", ""]
    (OUT / "SUSPECT_ITEMS.md").write_text("\n".join(L), encoding="utf-8")
    print(f"[suspects] {len(dump)} items -> {OUT / 'SUSPECT_ITEMS.md'}")
    print("[suspects] adjudicate every one before attributing any error to the model.")


def mode_depth4(pkg, results: dict) -> None:
    print("[depth4] 400 items, depths 1-4, seed 29 — the untested leaderboard cell")
    items = pkg["generate_compositional_items"](n_per_depth=100, max_depth=4, seed=29)
    llm = pkg["OpenAILLMModel"]()
    r = evaluate(pkg, llm, items, 29, "compositional_large::openai")
    results["compositional_large::openai"] = r
    print(f"[depth4] accuracy {r['accuracy']}  CI {r['wilson_95']}  ceiling={r['at_ceiling']}")
    for d, v in r["by_depth"].items():
        print(f"         depth {d}: {v['accuracy']} (n={v['n']}) CI {v['wilson_95']}")
    if r["at_ceiling"]:
        print("[depth4] STILL AT CEILING at depth 4. Task D does not discriminate. Run --hard.")


def mode_hard(pkg, results: dict, max_depth: int = 6, n_per: int = 60) -> None:
    print(f"[hard] sweeping depth 2..{max_depth}, {n_per} items per depth, to find where the ceiling breaks")
    llm = pkg["OpenAILLMModel"]()
    for depth in range(2, max_depth + 1):
        try:
            items = pkg["generate_compositional_items"](
                n_per_depth=n_per, max_depth=depth, seed=101 + depth)
        except Exception as e:
            print(f"[hard] depth {depth}: generator refused ({e}) — cap reached")
            break
        items = [it for it in items if getattr(it, "depth", depth) == depth] or items
        key = f"compositional_d{depth}::openai"
        r = evaluate(pkg, llm, items, 101 + depth, key)
        results[key] = r
        print(f"[hard] depth {depth}: acc {r['accuracy']} (n={r['n_items']}) CI {r['wilson_95']}")
        # Stop only once the depth is demonstrably off the ceiling: the whole interval has to
        # sit below 0.95. The looser "CI floor < 0.95" test is satisfied by any imperfect
        # n=60 sample, which ends the sweep after a single depth and yields no curve.
        if r["wilson_95"][1] < 0.95:
            print(f"[hard] ceiling breaks at depth {depth}. Build Task D around this depth.")
            break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump-suspects", action="store_true", help="no API calls")
    ap.add_argument("--depth4", action="store_true")
    ap.add_argument("--hard", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--yes", action="store_true", help="skip the spend confirmation")
    ap.add_argument("--max-depth", type=int, default=6)
    ap.add_argument("--n-per-depth", type=int, default=60)
    a = ap.parse_args()

    if not any([a.dump_suspects, a.depth4, a.hard, a.all]):
        ap.print_help()
        sys.exit(0)

    pkg = load_package()
    OUT.mkdir(parents=True, exist_ok=True)

    if a.dump_suspects or a.all:
        mode_dump_suspects(pkg)

    needs_api = a.depth4 or a.hard or a.all
    results: dict = {}
    if needs_api:
        est = (400 if (a.depth4 or a.all) else 0) + \
              ((a.max_depth - 1) * a.n_per_depth if (a.hard or a.all) else 0)
        before = cache_size()
        print(f"\n[cost] up to {est} completions; {before} cached responses on disk.")
        print("[cost] cached items are free; only new ones bill.")
        if not a.yes:
            if input("[cost] proceed? [y/N] ").strip().lower() not in ("y", "yes"):
                sys.exit("aborted")

        if a.depth4 or a.all:
            mode_depth4(pkg, results)
        if a.hard or a.all:
            mode_hard(pkg, results, a.max_depth, a.n_per_depth)

        payload = {
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "provenance": {
                "patients": "synthetic",
                "atoms": "ctgov",
                "is_oracle": False,
                "note": "Synthetic items over real ClinicalTrials.gov-derived atoms. "
                        "Not n2c2 patient records.",
            },
            "inference_parameters": {
                "requested_temperature": 0.0,
                "effective_temperature": "API default — gpt-5-nano rejects a custom temperature "
                                         "and the adapter drops it",
                "warning": "Do not report requested temperature as if it were applied.",
            },
            "cache_entries_before": before,
            "cache_entries_after": cache_size(),
            "runs": results,
        }
        (OUT / "missing_runs.json").write_text(json.dumps(payload, indent=2, default=str),
                                               encoding="utf-8")
        print(f"\n[wrote] {OUT / 'missing_runs.json'}")

        print("\n[summary]")
        for k, r in results.items():
            flag = "  <-- AT CEILING, does not discriminate" if r["at_ceiling"] else ""
            print(f"  {k:36s} acc={r['accuracy']} CI={r['wilson_95']} n={r['n_items']}{flag}")

    print("\nNext: python audit_paper_data.py results/missing/missing_runs.json")


if __name__ == "__main__":
    main()
