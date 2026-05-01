"""run_pipeline — end-to-end signal pipeline: ingest → rank → filter → hooks → ads."""
from __future__ import annotations
import json
import csv
import os

from backend.signals.ingest import ingest_all_sync
from backend.pipeline.rank import rank_signals
from backend.pipeline.filter import filter_signals, FILTER_KEYWORDS, ENGAGEMENT_THRESHOLD
from backend.pipeline.hooks import generate_hooks
from backend.pipeline.ads import format_ads

OUTPUT_JSON = "output_ads.json"
OUTPUT_CSV  = "output_ads.csv"

VALID_SOURCES = {"tiktok", "youtube", "meta", "google", "amazon", "google_trends", "linkedin"}


def run() -> dict:
    # 1. Ingest
    all_signals = ingest_all_sync()
    print(f"[ingest]  {len(all_signals)} signals from {len(VALID_SOURCES)} sources")

    # 2. Rank
    ranked = rank_signals(all_signals)

    # 3. Filter
    filtered = filter_signals(ranked)
    print(f"[filter]  {len(filtered)} signals passed ({len(FILTER_KEYWORDS)} keywords, "
          f"engagement >= {ENGAGEMENT_THRESHOLD})")

    # 4. Hooks
    hooks = generate_hooks(filtered)
    print(f"[hooks]   {len(hooks)} hooks generated")

    # 5. Ads
    ads = format_ads(hooks)
    print(f"[ads]     {len(ads)} ads formatted")

    # 6. Write JSON
    output = {
        "meta": {
            "total_signals": len(all_signals),
            "filtered_signals": len(filtered),
            "hooks": len(hooks),
            "ads": len(ads),
            "sources": sorted(VALID_SOURCES),
            "filter_keywords": FILTER_KEYWORDS,
        },
        "signals": [dict(s) for s in all_signals],
        "filtered": [dict(s) for s in filtered],
        "ads": ads,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"[output]  {OUTPUT_JSON} written ({os.path.getsize(OUTPUT_JSON):,} bytes)")

    # 7. Write CSV
    if ads:
        fieldnames = list(ads[0].keys())
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(ads)
        print(f"[output]  {OUTPUT_CSV} written ({len(ads)} rows)")

    return output


if __name__ == "__main__":
    run()
