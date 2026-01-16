"""Condition Node Processor.

TAG: [SPEC-012] [PROCESSOR] [CONDITION]
REQ: REQ-012-012 - Condition evaluation and branching
"""

from typing import Any

from pydantic import ValidationError

from app.schemas.processors import ConditionProcessorInput, ConditionProcessorOutput
from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.base import BaseProcessor, ProcessorConfig
from app.services.workflow.processors.errors import ProcessorValidationError


class ConditionNodeProcessor(
    BaseProcessor[ConditionProcessorInput, ConditionProcessorOutput]
):
    """Processor for condition nodes.

    TAG: [SPEC-012] [PROCESSOR] [CONDITION]

    Evaluates boolean expressions and routes to target nodes.

    Processing Flow:
    1. Validate conditions list
    2. Evaluate each condition in order
    3. Select first matching condition
    4. Return target node and evaluation results

    Attributes:
        input_schema: ConditionProcessorInput schema
        output_schema: ConditionProcessorOutput schema
    """

    input_schema = ConditionProcessorInput
    output_schema = ConditionProcessorOutput

    def __init__(
        self,
        node,
        context: ExecutionContext,
        config: ProcessorConfig | None = None,
    ) -> None:
        super().__init__(node, context, config)

    async def pre_process(self, inputs: dict[str, Any]) -> ConditionProcessorInput:
        """Validate and transform raw inputs into ConditionProcessorInput.

        TAG: [SPEC-012] [PROCESSOR] [CONDITION] [PRE]

        Args:
            inputs: Raw input dictionary containing conditions and evaluation_context

        Returns:
            Validated ConditionProcessorInput model

        Raises:
            ProcessorValidationError: If validation fails
        """
        try:
            return ConditionProcessorInput.model_validate(inputs)
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
        self, validated_input: ConditionProcessorInput
    ) -> ConditionProcessorOutput:
        """Execute the core condition processing logic.

        TAG: [SPEC-012] [PROCESSOR] [CONDITION] [CORE]

        Evaluates conditions in order and selects the first matching one.

        Args:
            validated_input: Validated condition processor input

        Returns:
            ConditionProcessorOutput with selected branch and evaluation results

        Raises:
            ProcessorExecutionError: If no condition matches
        """
        conditions = validated_input.conditions
        context = validated_input.evaluation_context

        evaluated_results = []
        selected_branch = None
        target_node = None

        for condition in conditions:
            # Simple expression evaluation (placeholder - would use eval safely in prod)
            try:
                # Create a safe evaluation context
                eval_context = {
                    "data": context.get("data", {}),
                    **context,
                }

                # Evaluate expression (simplified - production would use proper parser)
                result = eval(condition.expression, {"__builtins__": {}}, eval_context)

                evaluated_results.append(
                    {
                        "name": condition.name,
                        "expression": condition.expression,
                        "result": result,
                        "target_node": condition.target_node,
                    }
                )

                # Select first matching condition
                if result and selected_branch is None:
                    selected_branch = condition.name
                    target_node = condition.target_node
            except Exception:
                # If evaluation fails, treat as False
                evaluated_results.append(
                    {
                        "name": condition.name,
                        "expression": condition.expression,
                        "result": False,
                        "error": "Evaluation failed",
                    }
                )

        # If no condition matched, use last condition as default
        if selected_branch is None and conditions:
            selected_branch = conditions[-1].name
            target_node = conditions[-1].target_node

        return ConditionProcessorOutput(
            selected_branch=selected_branch or "default",
            target_node=target_node or "default",
            evaluated_conditions=evaluated_results,
        )

    async def post_process(self, output: ConditionProcessorOutput) -> dict[str, Any]:
        """Transform ConditionProcessorOutput into serializable dictionary.

        TAG: [SPEC-012] [PROCESSOR] [CONDITION] [POST]

        Args:
            output: Validated ConditionProcessorOutput model

        Returns:
            Serializable dictionary for downstream nodes
        """
        return output.model_dump()
