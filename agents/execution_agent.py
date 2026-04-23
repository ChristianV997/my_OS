def execute(decision):
    if not isinstance(decision, dict):
        raise TypeError("decision must be a dict")

    action = decision.get("action")

    if action == "launch":
        return "product launched"

    if action == "scale":
        return "budget increased"

    if action == "kill":
        return "campaign stopped"

    return "noop"
