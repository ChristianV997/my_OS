"""core.engine.master_loop — master execution + training loop.

Step 53: Full System Wiring

Runs execution_step() followed by a RL training step every cycle.
Evolution can be hooked in as a background task.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from core.engine.execution_loop import execution_step, buffer
from core.rl.policy import PolicyNet
from core.rl.trainer import RLTrainer
from core.rl.train_loop import train

_log = logging.getLogger(__name__)


def main_loop(
    get_state: Callable[[], dict[str, Any]],
    policy: PolicyNet | None = None,
    trainer: RLTrainer | None = None,
    interval: float = 60.0,
) -> None:
    """Run the master loop indefinitely.

    Parameters
    ----------
    get_state:
        Callable that returns the current raw state dict each cycle.
    policy:
        PolicyNet to update via training.  A new one is created if not provided.
    trainer:
        RLTrainer driving the update step.  Created from *policy* if not provided.
    interval:
        Seconds to sleep between cycles.
    """
    if policy is None:
        policy = PolicyNet()
    if trainer is None:
        trainer = RLTrainer(policy=policy)

    while True:
        state = get_state()

        # EXECUTION
        result = execution_step(state)
        _log.info("Execution result: %s", result.get("action"))

        # TRAINING
        train(policy, trainer)

        time.sleep(interval)
