import numpy as np


def apply_macro_override(base_regime: str, macro_signals: dict) -> str:
    """Apply FRED macro signal overrides to a base regime classification.

    Rules:
      - VIX > 30  → force ``"volatile"`` (fear gauge above stress threshold)
      - Negative GDP growth + base ``"stable"`` → force ``"decay"``

    Returns the (possibly overridden) regime string.
    """
    if not macro_signals:
        return base_regime

    vix = macro_signals.get("vix")
    gdp_growth = macro_signals.get("gdp_growth")

    if vix is not None and float(vix) > 30:
        return "volatile"

    if gdp_growth is not None and float(gdp_growth) < 0 and base_regime == "stable":
        return "decay"

    return base_regime


class RegimeDetector:

    def __init__(self, window=30):
        self.window = window

    def detect(self, event_log, macro_signals: dict | None = None):
        """Detect the current market regime from *event_log*.

        When *macro_signals* is provided (dict with ``vix`` and/or
        ``gdp_growth`` keys), FRED macro overrides are applied after the
        base classification.
        """
        rows = event_log.rows[-self.window:]

        if len(rows) < 10:
            return "unknown"

        roas = np.array([r.get("roas", 0) for r in rows])

        # variance
        var = np.var(roas)

        # trend (slope)
        x = np.arange(len(roas))
        slope = np.polyfit(x, roas, 1)[0]

        # volatility spikes
        diffs = np.diff(roas)
        volatility = np.std(diffs)

        # base classification
        if var < 0.02 and abs(slope) < 0.01:
            base = "stable"
        elif slope > 0.02:
            base = "growth"
        elif slope < -0.02:
            base = "decay"
        elif volatility > 0.1:
            base = "volatile"
        else:
            base = "neutral"

        return apply_macro_override(base, macro_signals or {})


detector = RegimeDetector()
