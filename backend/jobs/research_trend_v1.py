import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from backend.adapters.research import AdapterFetchError, GoogleTrendsAdapterV1, ResearchAdapterRegistry
from backend.jobs.runner import JobRegistry
from backend.research import TrendRecordStore

logger = logging.getLogger(__name__)


class AdapterMetrics:
    def __init__(self):
        self.counters = {
            "adapter_fetch_total": 0,
            "adapter_fetch_errors_total": 0,
            "adapter_records_fetched": 0,
        }

    def record_fetch(self, count: int):
        self.counters["adapter_fetch_total"] += 1
        self.counters["adapter_records_fetched"] += count

    def record_error(self):
        self.counters["adapter_fetch_errors_total"] += 1


def _source_enabled() -> bool:
    return str(os.getenv("FF_PILLAR_A_SOURCE_V1", "false")).strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def build_default_adapter_registry() -> ResearchAdapterRegistry:
    registry = ResearchAdapterRegistry()
    registry.register(
        GoogleTrendsAdapterV1.name,
        GoogleTrendsAdapterV1(
            max_pages=_int_env("PILLAR_A_SOURCE_V1_MAX_PAGES", 1),
            geo=os.getenv("PILLAR_A_SOURCE_V1_GEO", "US"),
            language=os.getenv("PILLAR_A_SOURCE_V1_LANG", "en-US"),
            timeout_seconds=_int_env("PILLAR_A_SOURCE_V1_TIMEOUT_SECONDS", 15),
            velocity_baseline=_float_env("PILLAR_A_SOURCE_V1_VELOCITY_BASELINE", 1000.0),
            confidence_baseline=_float_env("PILLAR_A_SOURCE_V1_CONFIDENCE_BASELINE", 0.7),
        ),
    )
    return registry


def register_research_trend_v1_job(
    job_registry: JobRegistry,
    *,
    adapter_registry: ResearchAdapterRegistry | None = None,
    store: TrendRecordStore | None = None,
    metrics: AdapterMetrics | None = None,
) -> None:
    adapters = adapter_registry or build_default_adapter_registry()
    record_store = store or TrendRecordStore()
    fetch_metrics = metrics or AdapterMetrics()
    adapter_name = GoogleTrendsAdapterV1.name

    def run_job() -> dict[str, Any]:
        if not _source_enabled():
            logger.info(
                {
                    "job": "research.trend.v1",
                    "adapter": adapter_name,
                    "status": "skipped",
                    "reason": "feature_flag_disabled",
                }
            )
            return {"status": "skipped", "records": 0}

        started = time.perf_counter()
        fetched_at = datetime.now(timezone.utc)

        try:
            adapter = adapters.get(adapter_name)
            raw_records = adapter.fetch()
            normalized_records = [adapter.to_canonical(record, fetched_at=fetched_at) for record in raw_records]
            persisted = record_store.append_many(normalized_records)
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            fetch_metrics.record_fetch(persisted)
            logger.info(
                {
                    "job": "research.trend.v1",
                    "adapter": adapter_name,
                    "status": "succeeded",
                    "record_count": persisted,
                    "duration_ms": duration_ms,
                }
            )
            return {"status": "succeeded", "records": persisted}
        except AdapterFetchError as err:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            fetch_metrics.record_error()
            logger.error(
                {
                    "job": "research.trend.v1",
                    "adapter": adapter_name,
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "error_type": err.error_type,
                    "error": str(err),
                    "context": err.context,
                }
            )
            raise

    job_registry.register("research.trend.v1", run_job)


def register_research_prune_job(job_registry: JobRegistry, *, store: TrendRecordStore | None = None) -> None:
    record_store = store or TrendRecordStore()

    def run_job() -> dict[str, Any]:
        deleted = record_store.pruneOldRecords()
        logger.info({"job": "research.prune", "status": "succeeded", "deleted_records": deleted})
        return {"status": "succeeded", "deleted_records": deleted}

    job_registry.register("research.prune", run_job)
