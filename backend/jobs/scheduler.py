import os
from datetime import datetime, timezone

from backend.jobs.runner import JobRegistry


class IngestionScheduler:
    def __init__(self, registry: JobRegistry, cron: str | None = None, feature_flag: str | None = None):
        self.registry = registry
        self.cron = cron or os.getenv("INGESTION_CRON", "0 * * * *")
        self.feature_flag = os.getenv("FF_PILLAR_A_INGESTION", "false") if feature_flag is None else feature_flag
        self._last_slot: str | None = None

    @property
    def is_enabled(self) -> bool:
        return str(self.feature_flag).strip().lower() in {"1", "true", "yes", "on"}

    def _window_name(self) -> str:
        minute, hour, *_ = self.cron.split()
        if minute == "*":
            return "minute"
        if hour == "*":
            return "hour"
        return "day"

    def _slot(self, now: datetime) -> str:
        window = self._window_name()
        if window == "minute":
            return now.strftime("%Y%m%d%H%M")
        if window == "hour":
            return now.strftime("%Y%m%d%H")
        return now.strftime("%Y%m%d")

    def should_run(self, now: datetime | None = None) -> bool:
        if not self.is_enabled:
            return False
        now = now or datetime.now(timezone.utc)
        slot = self._slot(now)
        if self._last_slot == slot:
            return False
        minute, hour, day, month, weekday = self.cron.split()
        checks = [
            (minute, now.minute),
            (hour, now.hour),
            (day, now.day),
            (month, now.month),
            (weekday, now.weekday()),
        ]
        return all(expr == "*" or int(expr) == value for expr, value in checks)

    def trigger_now(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now(timezone.utc)
        self._last_slot = self._slot(now)
        return self.registry.run_all(now=now, window=self._window_name())

    def tick(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now(timezone.utc)
        if not self.should_run(now=now):
            return []
        return self.trigger_now(now=now)
