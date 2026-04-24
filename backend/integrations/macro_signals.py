"""FRED / S&P macro signals — backend integration (Priority 2).

Fetches GDP growth, inflation (CPI), consumer sentiment (UMCSENT), and
VIX from the Federal Reserve Economic Data (FRED) REST API.  Results are
cached in-process to avoid excessive API calls.

Falls back to static stub values when the API key is absent or the network
is unavailable — ensuring the system always has a numeric macro context.

Environment variables:
  FRED_API_KEY   Free key from https://fred.stlouisfed.org/docs/api/api_key.html
  ICE_API_KEY    Optional S&P Global premium key (reserved for future use)

FRED series used:
  A191RL1Q225SBEA  Real GDP Percent Change (quarterly)
  CPIAUCSL         Consumer Price Index: All Urban Consumers
  UMCSENT          University of Michigan Consumer Sentiment
  VIXCLS           CBOE Volatility Index (VIX)
  DGS10            10-Year Treasury Constant Maturity Rate
"""
import datetime
import os

try:
    import requests as _requests
except ImportError:  # pragma: no cover
    _requests = None

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Stub values — approximate long-run averages (not investment advice)
_FALLBACK: dict[str, float] = {
    "gdp_growth": 2.5,
    "cpi_yoy": 3.2,
    "consumer_sentiment": 70.0,
    "vix": 18.0,
    "treasury_10y": 4.5,
    "macro_risk_score": 0.5,
}

_SERIES: dict[str, str] = {
    "gdp_growth": "A191RL1Q225SBEA",
    "cpi_yoy": "CPIAUCSL",
    "consumer_sentiment": "UMCSENT",
    "vix": "VIXCLS",
    "treasury_10y": "DGS10",
}

# In-process cache: (signals_dict, fetched_at)
_cache: tuple[dict, datetime.datetime] | None = None
_CACHE_TTL_MINUTES = 60


def _fetch_latest(series_id: str) -> float | None:
    """Return the most-recent non-missing observation for *series_id*."""
    if not FRED_API_KEY or _requests is None:
        return None

    now = datetime.datetime.now(datetime.timezone.utc).date()
    start = (now - datetime.timedelta(days=365)).isoformat()

    try:
        resp = _requests.get(
            _BASE,
            params={
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "observation_start": start,
                "sort_order": "desc",
                "limit": 5,
            },
            timeout=10,
        )
        resp.raise_for_status()
        for obs in resp.json().get("observations", []):
            val = obs.get("value", ".")
            if val != ".":
                return float(val)
        return None
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        return None


def _macro_risk(signals: dict) -> float:
    """Heuristic composite macro risk score in [0, 1].

    Combines VIX (fear gauge), CPI (inflation pressure), and consumer
    sentiment (demand signal) into a single risk score.  Higher → more risk.
    """
    vix = signals.get("vix", _FALLBACK["vix"])
    cpi = signals.get("cpi_yoy", _FALLBACK["cpi_yoy"])
    sentiment = signals.get("consumer_sentiment", _FALLBACK["consumer_sentiment"])

    # Normalise each driver to [0, 1]
    vix_norm = min(1.0, max(0.0, (vix - 10.0) / 50.0))         # 10=calm, 60=extreme fear
    cpi_norm = min(1.0, max(0.0, (cpi - 2.0) / 8.0))           # 2%=target, 10%=crisis
    sent_norm = min(1.0, max(0.0, (100.0 - sentiment) / 70.0))  # 100=high, 30=panic

    return round((vix_norm + cpi_norm + sent_norm) / 3.0, 4)


def get_macro_signals() -> dict:
    """Return macro indicator values with a composite risk score.

    Always succeeds — falls back to ``_FALLBACK`` values on any error.
    Results are cached in-process for ``_CACHE_TTL_MINUTES`` minutes.
    """
    global _cache

    now = datetime.datetime.now(datetime.timezone.utc)
    if _cache is not None:
        cached_signals, fetched_at = _cache
        if (now - fetched_at).total_seconds() < _CACHE_TTL_MINUTES * 60:
            return cached_signals

    signals: dict[str, float] = {}
    for key, series_id in _SERIES.items():
        val = _fetch_latest(series_id)
        signals[key] = val if val is not None else _FALLBACK[key]

    signals["macro_risk_score"] = _macro_risk(signals)

    _cache = (signals, now)
    return signals


def is_configured() -> bool:
    """True when a FRED API key is present."""
    return bool(FRED_API_KEY)
