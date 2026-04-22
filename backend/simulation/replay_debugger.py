import json

class SimulationReplayDebugger:
    def __init__(self, max_steps=200):
        self.buffer = []
        self.max_steps = max_steps

    def log_step(self, step_data: dict):
        self.buffer.append(step_data)
        if len(self.buffer) > self.max_steps:
            self.buffer.pop(0)

    def save(self, path="backend/simulation/replay_log.json"):
        with open(path, "w") as f:
            json.dump(self.buffer, f, indent=2)
        return path

    def replay(self, last_n=10):
        print("\n=== REPLAY DEBUG ===")
        for step in self.buffer[-last_n:]:
            print({
                "action": step.get("action"),
                "sim_roas": step.get("sim_roas"),
                "real_roas": step.get("real_roas"),
                "gap": step.get("gap"),
                "params": step.get("params")
            })

# global instance
replay_debugger = SimulationReplayDebugger()


def log_replay_step(action, sim_roas, real_roas, gap, params):
    replay_debugger.log_step({
        "action": action,
        "sim_roas": sim_roas,
        "real_roas": real_roas,
        "gap": gap,
        "params": params
    })
