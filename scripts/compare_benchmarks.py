#!/usr/bin/env python3
"""
Compare two benchmark JSON files (baseline vs candidate) and output
a markdown diff table for GitHub job summaries.
Exits 1 if a performance regression exceeds thresholds.
"""
import json
import sys


ROAS_DROP_THRESHOLD = -0.05       # absolute ROAS units
CAPITAL_DROP_THRESHOLD = -50.0    # dollars


def pct(base: float, cand: float) -> str:
    if base == 0:
        return "N/A"
    delta = ((cand - base) / abs(base)) * 100
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}%"


def emoji(base: float, cand: float, higher_is_better=True) -> str:
    better = cand >= base if higher_is_better else cand <= base
    return "✅" if better else "⚠️"


def main():
    if len(sys.argv) != 3:
        print("Usage: compare_benchmarks.py <baseline.json> <candidate.json>", file=sys.stderr)
        sys.exit(2)

    with open(sys.argv[1]) as f:
        base = json.load(f)
    with open(sys.argv[2]) as f:
        cand = json.load(f)

    roas_delta = cand["avg_roas"] - base["avg_roas"]
    capital_delta = cand["capital_gain"] - base["capital_gain"]
    regression = roas_delta < ROAS_DROP_THRESHOLD or capital_delta < CAPITAL_DROP_THRESHOLD

    print("## Benchmark: PR vs main")
    print()
    print(f"Each branch ran **{base['cycles']} cycles** from a clean state.")
    print()
    print("| Metric | main | PR | Δ | |")
    print("|--------|------|----|---|---|")

    rows = [
        ("Capital Gain",    base["capital_gain"],    cand["capital_gain"],    True,  "${:.2f}", "${:.2f}"),
        ("Avg ROAS",        base["avg_roas"],         cand["avg_roas"],         True,  "{:.4f}",  "{:.4f}"),
        ("ROAS Trend",      base["roas_trend_slope"], cand["roas_trend_slope"], True,  "{:+.4f}", "{:+.4f}"),
        ("Causal Edges",    base["causal_edges"],     cand["causal_edges"],     True,  "{}",      "{}"),
    ]
    for label, bv, cv, hib, bfmt, cfmt in rows:
        print(
            f"| {label} | {bfmt.format(bv)} | {cfmt.format(cv)} "
            f"| {pct(bv, cv)} | {emoji(bv, cv, hib)} |"
        )

    # Variant breakdown
    all_variants = sorted(
        set(list(base.get("variant_avg_roas", {}).keys()) +
            list(cand.get("variant_avg_roas", {}).keys()))
    )
    if all_variants:
        print()
        print("### Per-Variant ROAS")
        print()
        print("| Variant | main | PR | Δ |")
        print("|---------|------|----|---|")
        for v in all_variants:
            bv = base.get("variant_avg_roas", {}).get(v, 0.0)
            cv = cand.get("variant_avg_roas", {}).get(v, 0.0)
            print(f"| {v} | {bv:.4f} | {cv:.4f} | {pct(bv, cv)} |")

    print()
    if regression:
        print("> [!WARNING]")
        print("> **Performance regression detected.**")
        if roas_delta < ROAS_DROP_THRESHOLD:
            print(f"> - Avg ROAS dropped {roas_delta:.4f} (threshold {ROAS_DROP_THRESHOLD})")
        if capital_delta < CAPITAL_DROP_THRESHOLD:
            print(f"> - Capital gain dropped ${capital_delta:.2f} (threshold ${CAPITAL_DROP_THRESHOLD:.0f})")
        sys.exit(1)
    else:
        print("> [!NOTE]")
        print("> Performance is within acceptable range. ✅")


if __name__ == "__main__":
    main()
