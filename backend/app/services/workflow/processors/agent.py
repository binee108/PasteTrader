"""Agent Node Processor.

TAG: [SPEC-012] [PROCESSOR] [AGENT]
REQ: REQ-012-011 - Agent execution with LLM calls
"""

from typing import Any

from pydantic import ValidationError

from app.schemas.processors import AgentProcessorInput, AgentProcessorOutput
from app.services.workflow.context import ExecutionContext
from app.services.workflow.processors.base import BaseProcessor, ProcessorConfig
from app.services.workflow.processors.errors import ProcessorValidationError


class AgentNodeProcessor(BaseProcessor[AgentProcessorInput, AgentProcessorOutput]):
    """Processor for agent nodes.

    TAG: [SPEC-012] [PROCESSOR] [AGENT]

    Executes AI agents with LLM calls and prompt variables.

    Processing Flow:
    1. Validate agent_id and parameters
    2. Load agent configuration (will integrate with AgentService in SPEC-009)
    3. Build messages from prompt variables
    4. Execute LLM call (will integrate with LLM providers)
    5. Return formatted response with token usage

    Attributes:
        input_schema: AgentProcessorInput schema
        output_schema: AgentProcessorOutput schema
    """

    input_schema = AgentProcessorInput
    output_schema = AgentProcessorOutput

    def __init__(
        self,
        node,
        context: ExecutionContext,
        config: ProcessorConfig | None = None,
    ) -> None:
        super().__init__(node, context, config)

    async def pre_process(self, inputs: dict[str, Any]) -> AgentProcessorInput:
        """Validate and transform raw inputs into AgentProcessorInput.

        TAG: [SPEC-012] [PROCESSOR] [AGENT] [PRE]

        Args:
            inputs: Raw input dictionary containing agent_id, prompt_variables,
                   max_tokens, temperature

        Returns:
            Validated AgentProcessorInput model

        Raises:
            ProcessorValidationError: If validation fails
        """
        try:
            return AgentProcessorInput.model_validate(inputs)
        except ValidationError as e:
            # Convert ErrorDetails to dict for compatibility
            error_dicts = [
                {
                    "loc": list(err["loc"]),
                    "msg": err["msg"],
                    "type": err["type"],
                }
                for err in e.errors()
            ]
            raise ProcessorValidationError(
                processor=self.__class__.__name__,
                errors=error_dicts,
            )

    async def process(
        self, validated_input: AgentProcessorInput
    ) -> AgentProcessorOutput:
        """Execute the core agent processing logic.

        TAG: [SPEC-012] [PROCESSOR] [AGENT] [CORE]

        Note: Full AgentService integration will be implemented in SPEC-009.
        This implementation provides the structure with placeholder execution.

        Args:
            validated_input: Validated agent processor input

        Returns:
            AgentProcessorOutput with execution result

        Raises:
            ProcessorValidationError: If agent_id is not available
            ProcessorExecutionError: If agent execution fails
        """
        # TODO: Integrate with AgentService from SPEC-009
        # Current implementation is a structured stub that validates input

        agent_id = validated_input.agent_id
        prompt_variables = validated_input.prompt_variables

        # Placeholder: In full implementation, this would:
        # 1. Retrieve agent from AgentService: agent = await agent_service.get_agent(agent_id)
        # 2. Build messages from system_prompt and prompt_variables
        # 3. Execute LLM call with temperature/max_tokens parameters
        # 4. Return response with token usage

        # For now, return a structured placeholder response
        response = f"Agent {agent_id} executed with variables: {prompt_variables}"

        return AgentProcessorOutput(
            response=response,
            structured_output={"agent_id": agent_id, "variables": prompt_variables},
            token_usage={"prompt": 50, "completion": 100, "total": 150},
            model_used="claude-3-5-sonnet-20241022",
        )

    async def post_process(self, output: AgentProcessorOutput) -> dict[str, Any]:
        """Transform AgentProcessorOutput into serializable dictionary.

        TAG: [SPEC-012] [PROCESSOR] [AGENT] [POST]

        Args:
            output: Validated AgentProcessorOutput model

        Returns:
            Serializable dictionary for downstream nodes
        """
        return output.model_dump()
