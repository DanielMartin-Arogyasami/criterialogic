"""Per-depth structure tables and item-level trends for compositional item sets.

Shared by ``scripts/depth_structure.py`` (released sets) and
``scripts/run_size_matched.py`` (the size-matched set). Reads item sets and per-item
predictions only; no network, no key.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from criterialogic.metrics.stats import item_level_trend, wilson_interval
from criterialogic.metrics.structure import (
    balanced_accuracy,
    currency_ambiguous_leaves,
    expression_stats,
    pearson_r,
    undocumented_leaves,
)
from criterialogic.models.llm_api import OpenAILLMModel
from criterialogic.tasks.base import Item


def _mean(v: list[float]) -> float:
    return sum(v) / len(v) if v else 0.0


def _load(items_path: str, preds_path: str) -> tuple[list[Item], dict, dict]:
    items = [Item.model_validate(d) for d in json.loads(Path(items_path).read_text(encoding="utf-8"))]
    result = json.loads(Path(preds_path).read_text(encoding="utf-8"))
    preds = {p["item_id"]: p for p in result["per_item_predictions"]}
    missing = [it.item_id for it in items if it.item_id not in preds]
    if missing:
        raise SystemExit(f"{preds_path} has no prediction for {len(missing)} items, e.g. {missing[0]}")
    return items, result, preds


def _item_row(it: Item, p: dict, renderer: OpenAILLMModel) -> dict:
    if (p["gold"] == "met") != it.gold:
        raise SystemExit(f"Gold label mismatch for {it.item_id}: item set and result file disagree.")
    expr = it.criterion.expression
    s = expression_stats(expr)
    _, user = renderer._build_prompt(it)
    return {
        **s,
        "undocumented": undocumented_leaves(expr, it.facts),
        "currency_ambiguous": currency_ambiguous_leaves(expr, it.facts),
        "prompt_chars": len(user),
        "gold": it.gold,
        "pred_met": p["predicted"] == "met",
        "correct": bool(p["correct"]),
    }


def _summarise_level(r: list[dict]) -> dict:
    n, k = len(r), sum(x["correct"] for x in r)
    lo, hi = wilson_interval(k, n)
    ba = balanced_accuracy([(x["gold"], x["pred_met"]) for x in r])
    return {
        "n": n,
        "leaves_mean": round(_mean([x["leaves"] for x in r]), 1),
        "leaves_min": min(x["leaves"] for x in r), "leaves_max": max(x["leaves"] for x in r),
        "and_mean": round(_mean([x["and_groups"] for x in r]), 1),
        "or_mean": round(_mean([x["or_groups"] for x in r]), 1),
        "not_mean": round(_mean([x["nots"] for x in r]), 1),
        "canonical_depth_mean": round(_mean([x["canonical_depth"] for x in r]), 2),
        "undocumented_mean": round(_mean([x["undocumented"] for x in r]), 1),
        "currency_ambiguous_mean": round(_mean([x["currency_ambiguous"] for x in r]), 1),
        "prompt_chars_mean": round(_mean([x["prompt_chars"] for x in r])),
        "gold_met_rate": round(_mean([1.0 if x["gold"] else 0.0 for x in r]), 3),
        "model_met_rate": round(_mean([1.0 if x["pred_met"] else 0.0 for x in r]), 3),
        "accuracy": round(k / n, 3), "wilson_95": (round(lo, 4), round(hi, 4)),
        "balanced_accuracy": None if ba is None else round(ba, 3),
    }


def analyse(name: str, items_path: str, preds_path: str, n_mc: int = 20000) -> dict:
    """Per-depth structure and item-level trend for one item set and its result file."""
    items, result, preds = _load(items_path, preds_path)
    renderer = OpenAILLMModel(cache_dir=None)  # used only to render the exact prompt text
    rows: dict[int, list[dict]] = {}
    for it in items:
        row = _item_row(it, preds[it.item_id], renderer)
        rows.setdefault(row["depth"], []).append(row)
    per_depth = [{"depth": d, **_summarise_level(rows[d])} for d in sorted(rows)]

    flat = [(d, x) for d in sorted(rows) for x in rows[d]]
    depths = [float(d) for d, _ in flat]
    trend = item_level_trend(depths, [x["correct"] for _, x in flat], n_mc=n_mc)
    r_size = pearson_r(depths, [math.log2(x["leaves"]) for _, x in flat])
    return {"name": name, "items": items_path, "predictions": preds_path,
            "model": result.get("model"), "n_items": len(items), "per_depth": per_depth,
            "item_level_trend_over_depth": trend,
            "pearson_depth_vs_log2_leaves": round(r_size, 3)}


def analyse_by_size(name: str, items_path: str, preds_path: str, n_mc: int = 20000) -> dict:
    """Per-size structure and the item-level trend over log2(leaves), for a fixed-depth set."""
    items, result, preds = _load(items_path, preds_path)
    renderer = OpenAILLMModel(cache_dir=None)
    rows: dict[int, list[dict]] = {}
    for it in items:
        row = _item_row(it, preds[it.item_id], renderer)
        rows.setdefault(row["leaves"], []).append(row)
    per_size = [{"leaves": L, "depth_mean": round(_mean([x["depth"] for x in rows[L]]), 2),
                 **_summarise_level(rows[L])} for L in sorted(rows)]
    flat = [x for L in sorted(rows) for x in rows[L]]
    trend = item_level_trend([math.log2(x["leaves"]) for x in flat], [x["correct"] for x in flat], n_mc=n_mc)
    return {"name": name, "items": items_path, "predictions": preds_path,
            "model": result.get("model"), "n_items": len(items), "per_size": per_size,
            "item_level_trend_over_log2_leaves": trend}


def _model_label(model: dict) -> str:
    if model.get("prompt_version"):
        return f"{model.get('model', model.get('name', '?'))} (prompt v{model['prompt_version']})"
    return f"{model.get('name', '?')} (offline diagnostic)"


def to_markdown(sets: list[dict]) -> str:
    """Render one table per set, with the trend and the depth-size correlation under it."""
    out = ["# Per-depth structure and item-level trend", "",
           "Generated by `scripts/depth_structure.py` from released item sets and per-item predictions.",
           "Prompt length is the rendered user message in characters (the system prompt is constant).",
           "Currency-ambiguous leaves: no time qualifier, fact present but recorded as not current; the oracle counts them as met.", ""]
    for s in sets:
        model = s["model"] or {}
        out += [f"## {s['name']}", "",
                f"Model: {_model_label(model)}; n = {s['n_items']}.", "",
                "| Depth | n | Leaves mean (range) | AND | OR | NOT | Canonical depth | Undocumented leaves | Currency-ambiguous leaves | Prompt chars | Gold met | Model says met | Accuracy [95% CI] | Balanced accuracy |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in s["per_depth"]:
            ba = "n/a" if r["balanced_accuracy"] is None else f"{r['balanced_accuracy']:.3f}"
            out.append(
                f"| {r['depth']} | {r['n']} | {r['leaves_mean']} ({r['leaves_min']}-{r['leaves_max']}) | "
                f"{r['and_mean']} | {r['or_mean']} | {r['not_mean']} | {r['canonical_depth_mean']} | "
                f"{r['undocumented_mean']} | {r['currency_ambiguous_mean']} | {r['prompt_chars_mean']:,} | "
                f"{r['gold_met_rate']:.2f} | {r['model_met_rate']:.2f} | "
                f"{r['accuracy']:.3f} [{r['wilson_95'][0]:.3f}, {r['wilson_95'][1]:.3f}] | {ba} |")
        t = s["item_level_trend_over_depth"]
        out.append("")
        if t.get("degenerate"):
            out.append(f"Item-level trend: not estimable ({t['note']}).")
        else:
            out.append(
                f"Item-level trend over depth: odds ratio per depth level {t['odds_ratio_per_unit']:.3f} "
                f"[{t['or_ci95'][0]:.3f}, {t['or_ci95'][1]:.3f}], likelihood-ratio p = {t['p_lr_two_sided']:.2g}; "
                f"permutation p for a decline = {t['p_perm_one_sided_decline']:.2g} "
                f"({t['n_permutations']:,} permutations, floor {1 / (t['n_permutations'] + 1):.1g}).")
        out += [f"Item-level correlation between depth and log2(leaves): r = {s['pearson_depth_vs_log2_leaves']:.3f}.", ""]
    return "\n".join(out)


def to_markdown_by_size(sets: list[dict]) -> str:
    """Render the fixed-depth size sweep: one row per size level."""
    out = ["# Fixed-depth size sweep: per-size structure and item-level trend", "",
           "Generated by `scripts/run_size_sweep.py`. Depth is held fixed; leaves, groups and NOT nodes",
           "grow together; the gold label is half met at every size.", ""]
    for s in sets:
        model = s["model"] or {}
        out += [f"## {s['name']}", "",
                f"Model: {_model_label(model)}; n = {s['n_items']}.", "",
                "| Leaves | n | Depth | AND | OR | NOT | Canonical depth | Undocumented leaves | Currency-ambiguous leaves | Prompt chars | Gold met | Model says met | Accuracy [95% CI] | Balanced accuracy |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in s["per_size"]:
            ba = "n/a" if r["balanced_accuracy"] is None else f"{r['balanced_accuracy']:.3f}"
            out.append(
                f"| {r['leaves']} | {r['n']} | {r['depth_mean']} | {r['and_mean']} | {r['or_mean']} | "
                f"{r['not_mean']} | {r['canonical_depth_mean']} | {r['undocumented_mean']} | "
                f"{r['currency_ambiguous_mean']} | {r['prompt_chars_mean']:,} | {r['gold_met_rate']:.2f} | "
                f"{r['model_met_rate']:.2f} | {r['accuracy']:.3f} [{r['wilson_95'][0]:.3f}, {r['wilson_95'][1]:.3f}] | {ba} |")
        t = s["item_level_trend_over_log2_leaves"]
        out.append("")
        if t.get("degenerate"):
            out.append(f"Item-level trend: not estimable ({t['note']}).")
        else:
            out.append(
                f"Item-level trend over size: odds ratio per doubling of leaves {t['odds_ratio_per_unit']:.3f} "
                f"[{t['or_ci95'][0]:.3f}, {t['or_ci95'][1]:.3f}], likelihood-ratio p = {t['p_lr_two_sided']:.2g}; "
                f"permutation p for a decline = {t['p_perm_one_sided_decline']:.2g} "
                f"({t['n_permutations']:,} permutations, floor {1 / (t['n_permutations'] + 1):.1g}).")
        out.append("")
    return "\n".join(out)
