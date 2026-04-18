import json
from collections import deque

class RealityGapEngine:
    def __init__(self, window=100):
        self.sim = deque(maxlen=window)
        self.real = deque(maxlen=window)
        self.gap = deque(maxlen=window)
        self.smoothed_gap = None
        # tunable params for simulator
        self.params = {
            "noise_scale": 0.2,
            "trend_scale": 1.0,
            "delay_scale": 1.0,
        }
        self.max_step = {
            "noise_scale": 0.03,
            "trend_scale": 0.03,
            "delay_scale": 0.03,
        }

    def _bounded_update(self, key, target, lower, upper):
        current = self.params[key]
        step = max(-self.max_step[key], min(self.max_step[key], target - current))
        return min(upper, max(lower, current + step))

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
        if self.smoothed_gap is None:
            self.smoothed_gap = avg_gap
        else:
            self.smoothed_gap = 0.8 * self.smoothed_gap + 0.2 * avg_gap

        target_noise = self.params["noise_scale"]
        target_trend = self.params["trend_scale"]
        target_delay = self.params["delay_scale"]

        # adaptive rules with smoothing + bounded updates
        if self.smoothed_gap > 0.5:
            # simulation too far → increase noise + reduce trend confidence
            target_noise += 0.05
            target_trend -= 0.05
        elif self.smoothed_gap < 0.2:
            # simulation close → stabilize (less noise, stronger trend)
            target_noise -= 0.02
            target_trend += 0.02

        # delayed effects alignment (bias if sim lags/overshoots real)
        if len(self.real) >= 3 and len(self.sim) >= 3:
            real_trend = self.real[-1] - self.real[-3]
            sim_trend = self.sim[-1] - self.sim[-3]
            if abs(real_trend - sim_trend) > 0.3:
                # adjust delay sensitivity
                if sim_trend > real_trend:
                    target_delay -= 0.05
                else:
                    target_delay += 0.05

        self.params["noise_scale"] = self._bounded_update("noise_scale", target_noise, 0.05, 1.0)
        self.params["trend_scale"] = self._bounded_update("trend_scale", target_trend, 0.5, 2.0)
        self.params["delay_scale"] = self._bounded_update("delay_scale", target_delay, 0.5, 2.0)

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
