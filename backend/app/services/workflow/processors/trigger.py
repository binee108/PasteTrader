"""Trigger Node Processor.

TAG: [SPEC-012] [PROCESSOR] [TRIGGER]

Will be fully implemented in TASK-011.
"""

from app.services.workflow.processors.base import BaseProcessor


class TriggerNodeProcessor(BaseProcessor):
    """Processor for trigger nodes.

    TAG: [SPEC-012] [PROCESSOR] [TRIGGER]
    """

    def __init__(self, node, context, config=None):
        super().__init__(node, context, config)

    async def pre_process(self, inputs: dict) -> dict:
        """Validate and transform raw inputs."""
        return inputs

    async def process(self, validated_input: dict) -> dict:
        """Execute the core processing logic."""
        return {}

    async def post_process(self, output: dict) -> dict:
        """Transform output to serializable dict."""
        return output
