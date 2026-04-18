from core.intelligence_loop import run_intelligence
from tasks.pipeline import run_real_cycle


class Bridge:
    def execute(self, keywords):
        ideas = run_intelligence(keywords)

        for idea in ideas:
            product = {
                "name": idea[:30],
                "hook": "auto",
                "angle": "auto",
                "budget": 50,
            }
            run_real_cycle.delay(product)

        return len(ideas)
