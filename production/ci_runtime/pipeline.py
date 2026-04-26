from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from production.ci_runtime.replay_validation import (
    replay_validation_engine,
)

from production.ci_runtime.runtime_health import (
    runtime_health_engine,
)

from runtime.integration.runtime_kernel import (
    runtime_kernel,
)


class RuntimeCIPipeline:
    """
    Merge-safe runtime CI pipeline.
    """

    async def validate(
        self,
        correlation_id: str,
    ) -> Dict:
        kernel = await (
            runtime_kernel
            .initialize()
        )

        replay = await (
            replay_validation_engine
            .validate(
                correlation_id
            )
        )

        health = await (
            runtime_health_engine
            .evaluate()
        )

        deployment_ready = (
            replay.deterministic
            and health
            .deployment_ready
        )

        return {
            "deployment_ready": (
                deployment_ready
            ),
            "kernel_initialized": (
                kernel.initialized
            ),
            "replay_validation": (
                asdict(
                    replay
                )
            ),
            "runtime_health": (
                asdict(
                    health
                )
            ),
        }


runtime_ci_pipeline = (
    RuntimeCIPipeline()
)
