import json
from collections import deque

class RealityGapEngine:
    def __init__(self, window=100):
        self.sim = deque(maxlen=window)
        self.real = deque(maxlen=window)
        self.gap = deque(maxlen=window)
        # tunable params for simulator
        self.params = {
            "noise_scale": 0.2,
            "trend_scale": 1.0,
            "delay_scale": 1.0,
        }

    def update(self, simulated_roas: float, real_roas: float | None):
        """Update with latest simulated and (optional) real outcome."""
        self.sim.append(simulated_roas)
        if real_roas is not None:
            self.real.append(real_roas)
            gap = abs(simulated_roas - real_roas)
            self.gap.append(gap)
            return gap
        return None

    def summary(self):
        if not self.gap:
            return {"reality_gap": None}
        avg_gap = sum(self.gap) / len(self.gap)
        return {"reality_gap": round(avg_gap, 4)}

    def tune(self):
        """Adjust simulator parameters to reduce reality gap."""
        if len(self.gap) < 5:
            return self.params

        avg_gap = sum(self.gap) / len(self.gap)

        # simple adaptive rules (stable + monotonic)
        if avg_gap > 0.5:
            # simulation too far → increase noise + reduce trend confidence
            self.params["noise_scale"] = min(1.0, self.params["noise_scale"] + 0.05)
            self.params["trend_scale"] = max(0.5, self.params["trend_scale"] - 0.05)
        elif avg_gap < 0.2:
            # simulation close → stabilize (less noise, stronger trend)
            self.params["noise_scale"] = max(0.05, self.params["noise_scale"] - 0.02)
            self.params["trend_scale"] = min(2.0, self.params["trend_scale"] + 0.02)

        # delayed effects alignment (bias if sim lags/overshoots real)
        if len(self.real) >= 3 and len(self.sim) >= 3:
            real_trend = self.real[-1] - self.real[-3]
            sim_trend = self.sim[-1] - self.sim[-3]
            if abs(real_trend - sim_trend) > 0.3:
                # adjust delay sensitivity
                if sim_trend > real_trend:
                    self.params["delay_scale"] = max(0.5, self.params["delay_scale"] - 0.05)
                else:
                    self.params["delay_scale"] = min(2.0, self.params["delay_scale"] + 0.05)

        return self.params

    def export(self, path: str = "backend/simulation/reality_gap.json"):
        data = {
            "summary": self.summary(),
            "params": self.params,
            "samples": len(self.gap),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path


# Integration helper
reality_gap_engine = RealityGapEngine()


def apply_tuned_params(sim_env, params: dict):
    """Apply tuned parameters to simulation environment.
    Expect sim_env to expose attributes used below; ignore if absent.
    """
    for k, v in params.items():
        if hasattr(sim_env, k):
            setattr(sim_env, k, v)


# Example hook (to be called in execution loop)
def update_reality_gap(simulated_roas, real_roas, sim_env=None):
    gap = reality_gap_engine.update(simulated_roas, real_roas)
    params = reality_gap_engine.tune()
    if sim_env is not None:
        apply_tuned_params(sim_env, params)
    return gap, params
