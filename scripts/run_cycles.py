#!/usr/bin/env python3
"""
Active system runner with state persistence.
Loads previous state if available, runs N cycles, saves state, prints summary.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
import time

from backend.core.serializer import load, save
from backend.core.state import SystemState
from backend.execution.loop import run_cycle


def main():
    parser = argparse.ArgumentParser(description="Run MarketOS decision cycles")
    parser.add_argument("--cycles", type=int, default=200, help="Cycles to run")
    parser.add_argument("--state-path", default="state/state.json", help="State file path")
    args = parser.parse_args()

    state = load(args.state_path)
    if state is None:
        print("No existing state found — starting fresh.")
        state = SystemState()
    else:
        print(
            f"Restored state: {state.total_cycles:,} cycles, "
            f"capital={state.capital:.2f}, "
            f"events={len(state.event_log.rows):,}"
        )

    t0 = time.time()
    roas_trace = []

    for i in range(args.cycles):
        state = run_cycle(state)
        state.total_cycles += 1
        if state.event_log.rows:
            roas_trace.append(state.event_log.rows[-1].get("roas", 0))

    elapsed = time.time() - t0
    save(state, args.state_path)

    # Summary
    recent = state.event_log.rows[-100:]
    avg_roas = sum(r.get("roas", 0) for r in recent) / max(len(recent), 1)
    trend = roas_trace[-1] - roas_trace[0] if len(roas_trace) >= 2 else 0.0
    top_edges = sorted(
        state.graph.edges.items(), key=lambda x: abs(x[1]), reverse=True
    )[:3]

    print()
    print("=" * 50)
    print(f"  Cycles this run : {args.cycles}  ({elapsed:.1f}s)")
    print(f"  Total cycles    : {state.total_cycles:,}")
    print(f"  Capital         : ${state.capital:.2f}")
    print(f"  Avg ROAS (100)  : {avg_roas:.4f}")
    print(f"  ROAS trend      : {trend:+.4f}")
    print(f"  Causal edges    : {len(state.graph.edges)}")
    print(f"  Memory size     : {len(state.memory):,}")
    if top_edges:
        print("  Top causal edges:")
        for (p, c), w in top_edges:
            print(f"    {p} → {c}  w={w:.4f}")
    print("=" * 50)


if __name__ == "__main__":
    main()
