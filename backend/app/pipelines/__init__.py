"""Pipeline registry — maps pipeline names to their step definitions."""
from __future__ import annotations

from typing import Any, Callable, Coroutine

# Step handler signature:
#   async def step(*, job_id, config, prev_outputs, session) -> dict
StepHandler = Callable[..., Coroutine[Any, Any, dict[str, Any]]]


class PipelineDefinition:
    """Describes a pipeline's steps and their handlers."""

    def __init__(
        self,
        name: str,
        steps: list[tuple[str, StepHandler]],
    ) -> None:
        self.name = name
        self.steps = steps  # ordered list of (step_name, handler)

    @property
    def step_names(self) -> list[str]:
        return [name for name, _ in self.steps]

    def get_handler(self, step_name: str) -> StepHandler:
        for name, handler in self.steps:
            if name == step_name:
                return handler
        raise KeyError(f"Unknown step '{step_name}' in pipeline '{self.name}'")


# Global registry — populated by pipeline modules at import time
REGISTRY: dict[str, PipelineDefinition] = {}


def register(pipeline: PipelineDefinition) -> None:
    REGISTRY[pipeline.name] = pipeline


def get_pipeline(name: str) -> PipelineDefinition:
    if name not in REGISTRY:
        raise KeyError(f"Unknown pipeline '{name}'. Available: {list(REGISTRY.keys())}")
    return REGISTRY[name]


# Import pipeline modules to trigger registration
from app.pipelines import briefs as _briefs  # noqa: E402, F401
from app.pipelines import ad_copy as _ad_copy  # noqa: E402, F401
from app.pipelines import static_ads as _static_ads  # noqa: E402, F401
from app.pipelines import landing_pages as _landing_pages  # noqa: E402, F401
from app.pipelines import video_ugc as _video_ugc  # noqa: E402, F401
from app.pipelines import feedback_loop as _feedback_loop  # noqa: E402, F401
