from agents.execution_agent import execute
from core.cac import estimate_cac
from core.memory import store_event, store_pod_performance, store_product_result
from core.pods import pod_manager
from core.capital import capital_engine
from core.signals import signal_engine

# Launch offers only when estimated CAC is below 20 cost-units per conversion.
CAC_LAUNCH_THRESHOLD = 20


def run_cycle(signals=None):
    """Unified execution loop: Signals → Pods → Ads → Revenue → Memory → Decisions."""
    if signals is None:
        signals = signal_engine.get()

    for signal in signals or []:
        score = estimate_cac([signal])

        decision = {
            "action": "launch" if score < CAC_LAUNCH_THRESHOLD else "ignore",
        }

        result = execute(decision)

        if decision["action"] == "launch":
            budget = float(signal.get("budget", 50.0))
            pod = pod_manager.create(
                product=signal.get("product", "unknown"),
                market=signal.get("market", "global"),
                platform=signal.get("platform", "meta"),
                budget=budget,
            )
            roas = float(signal.get("roas", 0.0))
            spend = float(signal.get("spend", budget))
            revenue = roas * spend
            pod_manager.update_metrics(pod.id, roas=roas, spend=spend, revenue=revenue)
            capital_engine.apply(pod)

            store_pod_performance(pod.id, pod.metrics)
            store_product_result(
                pod.product,
                {"roas": roas, "spend": spend, "revenue": revenue, "status": pod.status},
            )

        store_event(
            {
                "signal": signal,
                "score": score,
                "decision": decision,
                "result": result,
            }
        )
