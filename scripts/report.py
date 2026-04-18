#!/usr/bin/env python3
"""
Generate a GitHub Actions job-summary markdown report from persisted state.
Usage: python scripts/report.py >> $GITHUB_STEP_SUMMARY
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backend.learning.bandit_update as bu
from backend.core.serializer import load

STATE_PATH = "state/state.json"


def variant_stats(rows):
    variants: dict[str, list[float]] = {}
    for r in rows:
        v = str(r.get("variant", "?"))
        variants.setdefault(v, []).append(float(r.get("roas", 0)))
    return {v: (sum(vals) / len(vals), len(vals)) for v, vals in sorted(variants.items())}


def capital_sparkline(memory, buckets=10):
    capitals = [r.get("capital_snapshot", None) for r in memory if "capital_snapshot" in r]
    if len(capitals) < 2:
        return "—"
    step = max(1, len(capitals) // buckets)
    bars = " ▁▂▃▄▅▆▇█"
    vals = capitals[::step][-buckets:]
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return "▄" * len(vals)
    return "".join(bars[int((v - lo) / (hi - lo) * 8)] for v in vals)


def main():
    state = load(STATE_PATH)
    if state is None:
        print("## MarketOS v4 — System Report")
        print()
        print("> No persisted state found. Run `scripts/run_cycles.py` first.")
        return

    recent = state.event_log.rows[-100:]
    avg_roas = sum(r.get("roas", 0) for r in recent) / max(len(recent), 1)
    v_stats = variant_stats(recent)
    top_edges = sorted(state.graph.edges.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
    bandit_table = sorted(
        [(k, sum(v) / len(v)) for k, v in bu.bandit_memory.history.items() if v],
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    print("## MarketOS v4 — System Report")
    print()
    print("### Overview")
    print()
    print("| Metric | Value |")
    print("|--------|-------|")
    print(f"| Total Cycles | {state.total_cycles:,} |")
    print(f"| Capital | ${state.capital:,.2f} |")
    print(f"| Capital vs Start | ${state.capital - 1000.0:+,.2f} |")
    print(f"| Avg ROAS (last 100) | {avg_roas:.4f} |")
    print(f"| Event Log Size | {len(state.event_log.rows):,} |")
    print(f"| Memory Size | {len(state.memory):,} |")
    print(f"| Causal Edges | {len(state.graph.edges)} |")
    print(f"| Regime | {state.regime} |")
    print()

    print("### Variant Performance (last 100 cycles)")
    print()
    print("| Variant | Avg ROAS | Executions |")
    print("|---------|----------|------------|")
    for v, (avg, count) in v_stats.items():
        print(f"| {v} | {avg:.4f} | {count} |")
    print()

    if top_edges:
        print("### Top Causal Edges")
        print()
        print("| From | To | Correlation |")
        print("|------|----|-------------|")
        for (p, c), w in top_edges:
            direction = "↑" if w > 0 else "↓"
            print(f"| `{p}` | `{c}` | {w:+.4f} {direction} |")
        print()

    if bandit_table:
        print("### Bandit Rankings (top actions by avg reward)")
        print()
        print("| Action | Avg Reward |")
        print("|--------|------------|")
        for k, avg in bandit_table:
            print(f"| `{k}` | {avg:.4f} |")
        print()

    print("### Energy")
    print()
    print(f"- Fatigue: `{state.energy.get('fatigue', 0):.3f}`")
    print(f"- Load: `{state.energy.get('load', 0):.3f}`")


if __name__ == "__main__":
    main()
