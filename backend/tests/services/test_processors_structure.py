"""Tests for processor directory structure.

TAG: [SPEC-012] [PROCESSOR] [TEST] [STRUCTURE]
REQ: REQ-012-A - File Structure
"""

import os
from pathlib import Path


class TestProcessorDirectoryStructure:
    """Test that processor directory structure exists and is properly organized."""

    def test_processors_directory_exists(self):
        """Test that the processors directory exists."""
        backend_path = Path(__file__).parent.parent.parent / "app"
        processors_path = backend_path / "services" / "workflow" / "processors"

        assert processors_path.exists(), f"Processors directory does not exist: {processors_path}"
        assert processors_path.is_dir(), f"Path is not a directory: {processors_path}"

    def test_processor_module_files_exist(self):
        """Test that all required processor module files exist."""
        backend_path = Path(__file__).parent.parent.parent / "app"
        processors_path = backend_path / "services" / "workflow" / "processors"

        required_files = [
            "__init__.py",
            "base.py",
            "errors.py",
            "metrics.py",
            "tool.py",
            "agent.py",
            "condition.py",
            "adapter.py",
            "trigger.py",
            "aggregator.py",
        ]

        for filename in required_files:
            file_path = processors_path / filename
            assert file_path.exists(), f"Required file does not exist: {filename}"
            assert file_path.is_file(), f"Path is not a file: {filename}"

    def test_processor_schemas_file_exists(self):
        """Test that the processor schemas file exists."""
        backend_path = Path(__file__).parent.parent.parent / "app"
        schemas_path = backend_path / "schemas"
        schemas_file = schemas_path / "processors.py"

        assert schemas_path.exists(), "Schemas directory does not exist"
        assert schemas_file.exists(), f"Processor schemas file does not exist: {schemas_file}"
        assert schemas_file.is_file(), f"Path is not a file: {schemas_file}"

    def test_processors_init_has_exports(self):
        """Test that processors __init__.py has proper exports."""
        backend_path = Path(__file__).parent.parent.parent / "app"
        init_file = backend_path / "services" / "workflow" / "processors" / "__init__.py"

        assert init_file.exists(), "__init__.py does not exist"

        content = init_file.read_text()

        # Check for key exports
        required_exports = [
            "ProcessorRegistry",
            "BaseProcessor",
            "ProcessorConfig",
        ]

        for export in required_exports:
            assert export in content, f"Missing export: {export}"
