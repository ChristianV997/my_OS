#!/usr/bin/env python3
"""
Run N cycles from a clean state and emit JSON metrics.
Used by CI benchmark and release workflows for reproducible comparisons.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
import json
import sys
import time

from backend.core.state import SystemState
from backend.execution.loop import run_cycle


def run_benchmark(cycles: int) -> dict:
    state = SystemState()
    capital_history = []
    roas_history = []

    t0 = time.time()
    for _ in range(cycles):
        state = run_cycle(state)
        capital_history.append(state.capital)
        if state.event_log.rows:
            roas_history.append(state.event_log.rows[-1].get("roas", 0))

    elapsed = time.time() - t0

    recent = state.event_log.rows[-50:]
    avg_roas = sum(r.get("roas", 0) for r in recent) / max(len(recent), 1)

    # per-variant avg
    variants: dict[str, list[float]] = {}
    for r in recent:
        v = str(r.get("variant", "?"))
        variants.setdefault(v, []).append(float(r.get("roas", 0)))
    variant_avg = {v: sum(vals) / len(vals) for v, vals in variants.items()}

    # ROAS trend (linear slope over last 20 readings)
    tail = roas_history[-20:] if len(roas_history) >= 20 else roas_history
    if len(tail) >= 2:
        n = len(tail)
        xs = list(range(n))
        xm = sum(xs) / n
        ym = sum(tail) / n
        slope = sum((xs[i] - xm) * (tail[i] - ym) for i in range(n)) / max(
            sum((xs[i] - xm) ** 2 for i in range(n)), 1e-9
        )
    else:
        slope = 0.0

    return {
        "cycles": cycles,
        "elapsed_s": round(elapsed, 2),
        "final_capital": round(state.capital, 4),
        "capital_gain": round(state.capital - 1000.0, 4),
        "avg_roas": round(avg_roas, 6),
        "roas_trend_slope": round(slope, 6),
        "causal_edges": len(state.graph.edges),
        "memory_size": len(state.memory),
        "variant_avg_roas": {k: round(v, 4) for k, v in variant_avg.items()},
    }


def main():
    parser = argparse.ArgumentParser(description="MarketOS benchmark runner")
    parser.add_argument("--cycles", type=int, default=100)
    parser.add_argument("--output", default="-", help="Output file path or - for stdout")
    args = parser.parse_args()

    metrics = run_benchmark(args.cycles)
    out = json.dumps(metrics, indent=2)

    if args.output == "-":
        print(out)
    else:
        with open(args.output, "w") as f:
            f.write(out)
        print(f"Benchmark written → {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
