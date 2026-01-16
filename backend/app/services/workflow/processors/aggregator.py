"""Aggregator Node Processor.

TAG: [SPEC-012] [PROCESSOR] [AGGREGATOR]
REQ: REQ-012-015 - Data aggregation from multiple sources
"""

from typing import Any

from pydantic import ValidationError

from app.schemas.processors import AggregatorProcessorInput, AggregatorProcessorOutput
from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.base import BaseProcessor, ProcessorConfig
from app.services.workflow.processors.errors import ProcessorValidationError


class AggregatorNodeProcessor(
    BaseProcessor[AggregatorProcessorInput, AggregatorProcessorOutput]
):
    """Processor for aggregator nodes.

    TAG: [SPEC-012] [PROCESSOR] [AGGREGATOR]

    Aggregates data from multiple input sources.

    Processing Flow:
    1. Validate aggregation strategy and sources
    2. Apply aggregation strategy to input sources
    3. Return aggregated result with source count

    Attributes:
        input_schema: AggregatorProcessorInput schema
        output_schema: AggregatorProcessorOutput schema
    """

    input_schema = AggregatorProcessorInput
    output_schema = AggregatorProcessorOutput

    def __init__(
        self,
        node,
        context: ExecutionContext,
        config: ProcessorConfig | None = None,
    ) -> None:
        super().__init__(node, context, config)

    async def pre_process(self, inputs: dict[str, Any]) -> AggregatorProcessorInput:
        """Validate and transform raw inputs into AggregatorProcessorInput.

        TAG: [SPEC-012] [PROCESSOR] [AGGREGATOR] [PRE]

        Args:
            inputs: Raw input dictionary containing strategy, input_sources,
                   aggregation_config

        Returns:
            Validated AggregatorProcessorInput model

        Raises:
            ProcessorValidationError: If validation fails
        """
        try:
            return AggregatorProcessorInput.model_validate(inputs)
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
        self, validated_input: AggregatorProcessorInput
    ) -> AggregatorProcessorOutput:
        """Execute the core aggregator processing logic.

        TAG: [SPEC-012] [PROCESSOR] [AGGREGATOR] [CORE]

        Applies the specified aggregation strategy to input sources.

        Args:
            validated_input: Validated aggregator processor input

        Returns:
            AggregatorProcessorOutput with aggregated result

        Raises:
            ProcessorExecutionError: If aggregation fails
        """
        strategy = validated_input.strategy
        input_sources = validated_input.input_sources
        config = validated_input.aggregation_config

        source_count = len(input_sources)
        aggregated_result: Any = None

        if strategy == "merge":
            # Merge all sources into single dict
            aggregated_result = {}
            for source_data in input_sources.values():
                if isinstance(source_data, dict):
                    aggregated_result.update(source_data)

        elif strategy == "list":
            # Collect all sources into list
            aggregated_result = []
            for source_data in input_sources.values():
                if isinstance(source_data, list):
                    aggregated_result.extend(source_data)
                else:
                    aggregated_result.append(source_data)

        elif strategy == "reduce":
            # Reduce sources using operation
            operation = config.get("operation", "sum")
            values = list(input_sources.values())

            if operation == "sum":
                aggregated_result = sum(values)
            elif operation == "concatenate":
                aggregated_result = "".join(str(v) for v in values)
            elif operation == "average":
                aggregated_result = sum(values) / len(values) if values else 0
            else:
                aggregated_result = values

        else:  # custom
            # Custom aggregation - pass through
            aggregated_result = {"sources": input_sources}

        return AggregatorProcessorOutput(
            aggregated_result=aggregated_result,
            source_count=source_count,
            strategy_used=strategy,
        )

    async def post_process(self, output: AggregatorProcessorOutput) -> dict[str, Any]:
        """Transform AggregatorProcessorOutput into serializable dictionary.

        TAG: [SPEC-012] [PROCESSOR] [AGGREGATOR] [POST]

        Args:
            output: Validated AggregatorProcessorOutput model

        Returns:
            Serializable dictionary for downstream nodes
        """
        return output.model_dump()
