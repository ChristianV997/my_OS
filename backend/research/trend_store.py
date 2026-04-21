import json
import os
from typing import Any


class TrendRecordStore:
    def __init__(self, path: str = "backend/state/research_trends.jsonl"):
        self.path = path

    def append_many(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return len(records)
