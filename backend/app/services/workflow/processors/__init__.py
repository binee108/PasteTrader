"""Node Processor Framework - Processors Module.

TAG: [SPEC-012] [PROCESSOR] [INIT]

This module provides the processor registry and exports for all node processors.
"""

from app.services.workflow.processors.base import BaseProcessor, ProcessorConfig
from app.services.workflow.processors.registry import ProcessorRegistry

__all__ = [
    "BaseProcessor",
    "ProcessorConfig",
    "ProcessorRegistry",
]
