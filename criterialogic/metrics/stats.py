"""stats.py — the uncertainty machinery every reported number goes through.

A benchmark this small cannot report bare point estimates. Sixty items per depth puts
a Wilson interval roughly ±0.12 wide, which is the difference between "accuracy falls
with nesting depth" and "these two depths are indistinguishable at this sample size".
Everything here exists so the manuscript can state which of those two it has.

Implemented with the standard library only — no numpy, no scipy — so that a reviewer
can read the arithmetic and a CI run needs no scientific stack.

Contents
--------
``wilson_interval``      binomial CI that stays inside [0, 1] at p = 0 or 1, where the
                         normal approximation degenerates. Perfect scores are common
                         here, so this is not a stylistic preference.
``spearman_rho``         rank correlation, tie-corrected via average ranks.
``permutation_p``        exact one-sided p over all orderings when the number of levels
                         is small (<= 8), Monte Carlo otherwise. With five depth levels
                         there are 120 orderings, so "exact" is literally exact.
``n_per_group_needed``   the per-group n that would separate two proportions at
                         80% power — the honest answer to "why don't you claim this".
``expected_calibration_error`` / ``selective_accuracy`` calibration and abstention,
                         the latter tie-aware (see the docstring for why that matters).
``cohens_kappa`` / ``kappa_with_ci`` inter-annotator agreement with a bootstrap
                         interval and a per-category breakdown.
"""
from __future__ import annotations

import math
import random
from collections import Counter
from itertools import permutations

Z95 = 1.959963984540054

# --------------------------------------------------------------------------- #
# Proportions
# --------------------------------------------------------------------------- #
def wilson_interval(successes: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Chosen over the Wald interval because the benchmark routinely produces 0 and 1:
    Wald gives a zero-width interval there, which would read as certainty from a
    sample of 60.
    """
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = (centre - half) / denom
    hi = (centre + half) / denom
    # At p = 0 or p = 1 the bound is exactly 0 or 1, but the arithmetic lands a few ulps
    # away, and an interval printed as [0.9398, 0.9999999999999998] reads as a bug.
    if hi > 1.0 - 1e-9:
        hi = 1.0
    if lo < 1e-9:
        lo = 0.0
    return (max(0.0, lo), min(1.0, hi))


def intervals_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return not (a[1] < b[0] or b[1] < a[0])


def n_per_group_needed(p1: float, p2: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Per-group n to detect the difference between two proportions at ``power``.

    Standard two-proportion normal approximation. Returns -1 when the proportions are
    equal (no effect to size). Reported alongside overlapping intervals so a reader can
    see what it would take to settle the comparison rather than only that it is unsettled.
    """
    if abs(p1 - p2) < 1e-12:
        return -1
    z_a = Z95 if abs(alpha - 0.05) < 1e-9 else _z_from_two_sided_alpha(alpha)
    z_b = 0.8416212335729143 if abs(power - 0.80) < 1e-9 else _z_from_power(power)
    pbar = (p1 + p2) / 2.0
    num = (z_a * math.sqrt(2 * pbar * (1 - pbar)) + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return max(1, math.ceil(num / (p1 - p2) ** 2))


def _inv_norm_cdf(p: float) -> float:
    """Acklam's rational approximation to the normal quantile (|error| < 1.15e-9)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _z_from_two_sided_alpha(alpha: float) -> float:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1); got {alpha}.")
    return _inv_norm_cdf(1 - alpha / 2)


def _z_from_power(power: float) -> float:
    if not 0.0 < power < 1.0:
        # Power of exactly 1 requires an infinite sample; the caller wants a number.
        raise ValueError(f"power must be in (0, 1); got {power}.")
    return _inv_norm_cdf(power)


# --------------------------------------------------------------------------- #
# Rank correlation and permutation testing
# --------------------------------------------------------------------------- #
def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def spearman_rho(x: list[float], y: list[float]) -> float:
    """Tie-corrected Spearman rank correlation. Returns 0.0 when either side is constant."""
    if len(x) != len(y):
        raise ValueError("x and y must be the same length")
    n = len(x)
    if n < 2:
        return 0.0
    rx, ry = _average_ranks(list(x)), _average_ranks(list(y))
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


EXACT_PERMUTATION_MAX_LEVELS = 8


def permutation_p(x: list[float], y: list[float], n_mc: int = 20000,
                  seed: int = 0) -> dict:
    """One-sided p for ``rho <= observed`` (i.e. a decline) by permuting ``y``.

    Exact over all ``len(y)!`` orderings when that is tractable, Monte Carlo above the
    cutoff. The mode is returned so a table can say which it was: with five depth
    levels the smallest attainable exact p is 1/120 = 0.0083, and a reader should be
    able to see that floor rather than infer it.
    """
    observed = spearman_rho(x, y)
    if len(y) <= EXACT_PERMUTATION_MAX_LEVELS:
        orderings = list(permutations(y))
        hits = sum(1 for perm in orderings if spearman_rho(x, list(perm)) <= observed + 1e-12)
        return {"rho": observed, "p_one_sided": hits / len(orderings),
                "mode": "exact", "n_permutations": len(orderings),
                "min_attainable_p": 1.0 / len(orderings)}
    rng = random.Random(seed)
    pool = list(y)
    hits = 0
    for _ in range(n_mc):
        rng.shuffle(pool)
        if spearman_rho(x, pool) <= observed + 1e-12:
            hits += 1
    return {"rho": observed, "p_one_sided": (hits + 1) / (n_mc + 1),
            "mode": "monte_carlo", "n_permutations": n_mc,
            "min_attainable_p": 1.0 / (n_mc + 1)}


def depth_trend(per_depth: dict[int, tuple[int, int]]) -> dict:
    """Summarise an accuracy-versus-depth curve.

    ``per_depth`` maps depth -> (n_correct, n). Returns per-depth accuracy with Wilson
    intervals, the rank correlation with its permutation p, whether the decline is
    monotonic, and for every pair whose intervals overlap the per-depth n that would
    separate them. That last field is what stops a non-significant comparison from
    being written up as a finding.
    """
    depths = sorted(per_depth)
    rows = []
    for d in depths:
        k, n = per_depth[d]
        rows.append({"depth": d, "n": n, "accuracy": (k / n) if n else 0.0,
                     "wilson_95": tuple(round(v, 4) for v in wilson_interval(k, n))})
    accs = [r["accuracy"] for r in rows]
    trend = permutation_p([float(d) for d in depths], accs)
    pairwise = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            overlap = intervals_overlap(a["wilson_95"], b["wilson_95"])
            pairwise.append({
                "depths": (a["depth"], b["depth"]),
                "accuracies": (round(a["accuracy"], 4), round(b["accuracy"], 4)),
                "cis_overlap": overlap,
                "n_per_depth_needed": n_per_group_needed(a["accuracy"], b["accuracy"]) if overlap else 0,
            })
    return {
        "per_depth": rows,
        "spearman": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in trend.items()},
        "monotonic_non_increasing": all(accs[i] >= accs[i + 1] - 1e-12 for i in range(len(accs) - 1)),
        "pairwise": pairwise,
    }


# --------------------------------------------------------------------------- #
# Calibration and abstention
# --------------------------------------------------------------------------- #
def expected_calibration_error(rows: list[tuple[float, bool]], n_bins: int = 10) -> float:
    """ECE over equal-width confidence bins. ``rows`` is [(confidence, correct)]."""
    if not rows:
        return 0.0
    n = len(rows)
    total = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        bucket = [(c, ok) for c, ok in rows if (lo < c <= hi) or (b == 0 and c == 0.0)]
        if not bucket:
            continue
        conf = sum(c for c, _ in bucket) / len(bucket)
        acc = sum(1 for _, ok in bucket if ok) / len(bucket)
        total += (len(bucket) / n) * abs(acc - conf)
    return total


def is_degenerate_confidence(rows: list[tuple[float, bool]]) -> bool:
    """True when every prediction carries the same confidence.

    A model like that has no abstention signal at all, and any selective-accuracy
    curve computed from it is an artefact of list order. The audit of the v0.1 results
    found exactly this reported as a calibration finding, so the check is a gate rather
    than a diagnostic.
    """
    return len({round(c, 12) for c, _ in rows}) <= 1


def selective_accuracy(rows: list[tuple[float, bool]],
                       coverages: tuple[float, ...] = (0.1, 0.2, 0.3, 0.4, 0.5,
                                                       0.6, 0.7, 0.8, 0.9, 1.0)) -> dict:
    """Tie-aware accuracy versus coverage.

    Items are ranked by confidence descending. Where a tie block straddles the coverage
    boundary the expected accuracy over random tie-breaking is used, rather than
    whichever tied item happened to come first in the list. Without this, a
    constant-confidence model appears to have a sloping curve.
    """
    if not rows:
        return {}
    ordered = sorted(rows, key=lambda r: -r[0])
    n = len(ordered)
    out: dict = {}
    for cov in coverages:
        k = max(1, round(n * cov))
        threshold = ordered[k - 1][0]
        above = [r for r in ordered if r[0] > threshold]
        tied = [r for r in ordered if r[0] == threshold]
        expected_correct = sum(1 for _, ok in above if ok)
        need = k - len(above)
        if tied and need > 0:
            expected_correct += need * (sum(1 for _, ok in tied if ok) / len(tied))
        out[f"{int(round(cov * 100))}%"] = round(expected_correct / k, 4)
    out["degenerate_single_bin"] = is_degenerate_confidence(rows)
    return out


# --------------------------------------------------------------------------- #
# Inter-annotator agreement
# --------------------------------------------------------------------------- #
def cohens_kappa(a: list[str], b: list[str]) -> float:
    """Cohen's kappa between two aligned lists of categorical labels."""
    if len(a) != len(b):
        raise ValueError("label lists must be the same length")
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    categories = set(a) | set(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in categories)
    if pe >= 1.0 - 1e-12:
        # Both raters used one identical category throughout: chance agreement is
        # already total, so kappa is undefined. Reporting 1.0 would overstate it;
        # reporting 0.0 would understate it. The caller is told instead.
        return float("nan")
    return (po - pe) / (1 - pe)


def percent_agreement(a: list[str], b: list[str]) -> float:
    if len(a) != len(b):
        raise ValueError("label lists must be the same length")
    return sum(1 for x, y in zip(a, b) if x == y) / len(a) if a else 0.0


def kappa_with_ci(a: list[str], b: list[str], n_boot: int = 5000,
                  seed: int = 0, alpha: float = 0.05) -> dict:
    """Cohen's kappa with a percentile bootstrap CI over items.

    Bootstrap rather than the analytic standard error because the category
    distribution here is skewed and sparse: with most errors falling into two of seven
    categories, the asymptotic SE is not trustworthy at n = 150-200.
    """
    point = cohens_kappa(a, b)
    n = len(a)
    if n == 0:
        return {"n": 0, "kappa": float("nan"), "ci_95": (float("nan"), float("nan")),
                "percent_agreement": 0.0, "n_bootstrap": 0}
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        k = cohens_kappa([a[i] for i in idx], [b[i] for i in idx])
        if not math.isnan(k):
            draws.append(k)
    draws.sort()
    if draws:
        lo = draws[max(0, int((alpha / 2) * len(draws)) - 1)]
        hi = draws[min(len(draws) - 1, int((1 - alpha / 2) * len(draws)))]
    else:
        lo = hi = float("nan")
    return {
        "n": n,
        "kappa": round(point, 4) if not math.isnan(point) else None,
        "ci_95": (round(lo, 4), round(hi, 4)) if draws else (None, None),
        "percent_agreement": round(percent_agreement(a, b), 4),
        "n_bootstrap": len(draws),
    }


def per_category_agreement(a: list[str], b: list[str]) -> dict:
    """One-vs-rest kappa and agreement for each category either annotator used.

    A single pooled kappa hides the case that matters: high overall agreement carried
    by one dominant category while the categories the taxonomy exists to distinguish
    are the ones the annotators disagree on.
    """
    out: dict = {}
    for cat in sorted(set(a) | set(b)):
        ba = ["yes" if x == cat else "no" for x in a]
        bb = ["yes" if x == cat else "no" for x in b]
        k = cohens_kappa(ba, bb)
        out[cat] = {
            "n_annotator_1": sum(1 for x in a if x == cat),
            "n_annotator_2": sum(1 for x in b if x == cat),
            "n_both": sum(1 for x, y in zip(a, b) if x == cat and y == cat),
            "kappa_one_vs_rest": round(k, 4) if not math.isnan(k) else None,
            "percent_agreement": round(percent_agreement(ba, bb), 4),
        }
    return out
