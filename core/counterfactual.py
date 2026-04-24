class CounterfactualEngine:
    def __init__(self, causal_model):
        self.model = causal_model

    def evaluate(self, state, actions):
        results = {}

        for name, action in actions.items():
            effect = self.model.estimate_effect(action)
            results[name] = effect

        return results
