"""Trigger Node Processor.

TAG: [SPEC-012] [PROCESSOR] [TRIGGER]
REQ: REQ-012-014 - Trigger initialization and execution
"""

from datetime import datetime, UTC
from typing import Any

from pydantic import ValidationError

from app.schemas.processors import TriggerProcessorInput, TriggerProcessorOutput
from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.base import BaseProcessor, ProcessorConfig
from app.services.workflow.processors.errors import ProcessorValidationError


class TriggerNodeProcessor(
    BaseProcessor[TriggerProcessorInput, TriggerProcessorOutput]
):
    """Processor for trigger nodes.

    TAG: [SPEC-012] [PROCESSOR] [TRIGGER]

    Initializes workflow execution from various trigger sources.

    Processing Flow:
    1. Validate trigger type and payload
    2. Initialize context variables from trigger
    3. Return trigger status and initialization timestamp

    Attributes:
        input_schema: TriggerProcessorInput schema
        output_schema: TriggerProcessorOutput schema
    """

    input_schema = TriggerProcessorInput
    output_schema = TriggerProcessorOutput

    def __init__(
        self,
        node,
        context: ExecutionContext,
        config: ProcessorConfig | None = None,
    ) -> None:
        super().__init__(node, context, config)

    async def pre_process(self, inputs: dict[str, Any]) -> TriggerProcessorInput:
        """Validate and transform raw inputs into TriggerProcessorInput.

        TAG: [SPEC-012] [PROCESSOR] [TRIGGER] [PRE]

        Args:
            inputs: Raw input dictionary containing trigger_type,
                   trigger_payload, trigger_metadata

        Returns:
            Validated TriggerProcessorInput model

        Raises:
            ProcessorValidationError: If validation fails
        """
        try:
            return TriggerProcessorInput.model_validate(inputs)
        except ValidationError as e:
            error_dicts = [
                {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
                for err in e.errors()
            ]
            raise ProcessorValidationError(
                processor=self.__class__.__name__,
                errors=error_dicts,
            )

    async def process(
        self, validated_input: TriggerProcessorInput
    ) -> TriggerProcessorOutput:
        """Execute the core trigger processing logic.

        TAG: [SPEC-012] [PROCESSOR] [TRIGGER] [CORE]

        Initializes the workflow based on trigger type.

        Args:
            validated_input: Validated trigger processor input

        Returns:
            TriggerProcessorOutput with initialization status

        Raises:
            ProcessorValidationError: If trigger type is not supported
        """
        trigger_type = validated_input.trigger_type
        payload = validated_input.trigger_payload
        metadata = validated_input.trigger_metadata

        context_variables = {}
        trigger_timestamp = datetime.now(UTC)

        # Process different trigger types
        if trigger_type == "webhook":
            context_variables = {
                "trigger_source": "webhook",
                "webhook_payload": payload,
                "webhook_metadata": metadata,
            }
        elif trigger_type == "schedule":
            context_variables = {
                "trigger_source": "schedule",
                "schedule_id": payload.get("schedule_id", "unknown"),
                "scheduled_time": trigger_timestamp.isoformat(),
            }
        elif trigger_type == "manual":
            context_variables = {
                "trigger_source": "manual",
                "user_id": payload.get("user_id", "unknown"),
                "manual_trigger_time": trigger_timestamp.isoformat(),
            }
        else:
            # Unknown trigger type - pass through payload
            context_variables = {
                "trigger_source": trigger_type,
                "payload": payload,
                "metadata": metadata,
            }

        return TriggerProcessorOutput(
            initialized=True,
            context_variables=context_variables,
            trigger_timestamp=trigger_timestamp,
        )

    async def post_process(self, output: TriggerProcessorOutput) -> dict[str, Any]:
        """Transform TriggerProcessorOutput into serializable dictionary.

        TAG: [SPEC-012] [PROCESSOR] [TRIGGER] [POST]

        Args:
            output: Validated TriggerProcessorOutput model

        Returns:
            Serializable dictionary for downstream nodes
        """
        return output.model_dump()
