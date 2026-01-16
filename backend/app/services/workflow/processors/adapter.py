"""Adapter Node Processor.

TAG: [SPEC-012] [PROCESSOR] [ADAPTER]
REQ: REQ-012-013 - Data transformation with adapters
"""

from typing import Any

from pydantic import ValidationError

from app.models.workflow import Node
from app.schemas.processors import AdapterProcessorInput, AdapterProcessorOutput
from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.base import BaseProcessor, ProcessorConfig
from app.services.workflow.processors.errors import ProcessorValidationError


class AdapterNodeProcessor(
    BaseProcessor[AdapterProcessorInput, AdapterProcessorOutput]
):
    """Processor for adapter nodes.

    TAG: [SPEC-012] [PROCESSOR] [ADAPTER]

    Transforms data using various transformation strategies.

    Processing Flow:
    1. Validate transformation type and config
    2. Apply transformation to source data
    3. Return transformed data with metadata

    Attributes:
        input_schema: AdapterProcessorInput schema
        output_schema: AdapterProcessorOutput schema
    """

    input_schema = AdapterProcessorInput
    output_schema = AdapterProcessorOutput

    def __init__(
        self,
        node: Node,
        context: ExecutionContext,
        config: ProcessorConfig | None = None,
    ) -> None:
        super().__init__(node, context, config)

    async def pre_process(self, inputs: dict[str, Any]) -> AdapterProcessorInput:
        """Validate and transform raw inputs into AdapterProcessorInput.

        TAG: [SPEC-012] [PROCESSOR] [ADAPTER] [PRE]

        Args:
            inputs: Raw input dictionary containing transformation_type,
                   source_data, transformation_config

        Returns:
            Validated AdapterProcessorInput model

        Raises:
            ProcessorValidationError: If validation fails
        """
        try:
            return AdapterProcessorInput.model_validate(inputs)
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
        self, validated_input: AdapterProcessorInput
    ) -> AdapterProcessorOutput:
        """Execute the core adapter processing logic.

        TAG: [SPEC-012] [PROCESSOR] [ADAPTER] [CORE]

        Applies the specified transformation to source data.

        Args:
            validated_input: Validated adapter processor input

        Returns:
            AdapterProcessorOutput with transformed data

        Raises:
            ProcessorExecutionError: If transformation fails
        """
        transformation_type = validated_input.transformation_type
        source_data = validated_input.source_data
        config = validated_input.transformation_config

        transformed_data = source_data
        records_processed = 0

        if transformation_type == "field_mapping":
            # Apply field mapping
            mapping = config.get("mapping", {})
            if isinstance(source_data, dict):
                transformed_data = {}
                for old_key, new_key in mapping.items():
                    if old_key in source_data:
                        transformed_data[new_key] = source_data[old_key]
                records_processed = len(source_data)

        elif transformation_type == "type_conversion":
            # Apply type conversions
            conversions = config.get("conversions", {})
            if isinstance(source_data, dict):
                transformed_data = source_data.copy()
                for field, target_type in conversions.items():
                    if field in transformed_data:
                        if target_type == "integer":
                            transformed_data[field] = int(transformed_data[field])
                        elif target_type == "string":
                            transformed_data[field] = str(transformed_data[field])
                        elif target_type == "float":
                            transformed_data[field] = float(transformed_data[field])
                records_processed = len(source_data)

        elif transformation_type == "filtering":
            # Apply filtering
            filter_expr = config.get("filter", "")
            if isinstance(source_data, dict) and "items" in source_data:
                items = source_data["items"]
                # Simplified filtering - production would use proper parser
                if ">" in filter_expr:
                    threshold = int(filter_expr.split(">")[-1].strip())
                    transformed_data = {"items": [x for x in items if x > threshold]}
                    records_processed = len(items)
            else:
                records_processed = 1

        elif transformation_type == "aggregation":
            # Apply aggregation
            if isinstance(source_data, dict):
                transformed_data = {"aggregated": len(source_data)}
                records_processed = len(source_data)

        else:  # custom
            # Custom transformation - just pass through
            records_processed = 1

        return AdapterProcessorOutput(
            transformed_data=transformed_data,
            transformation_applied=transformation_type,
            records_processed=records_processed,
        )

    async def post_process(self, output: AdapterProcessorOutput) -> dict[str, Any]:
        """Transform AdapterProcessorOutput into serializable dictionary.

        TAG: [SPEC-012] [PROCESSOR] [ADAPTER] [POST]

        Args:
            output: Validated AdapterProcessorOutput model

        Returns:
            Serializable dictionary for downstream nodes
        """
        return output.model_dump()
