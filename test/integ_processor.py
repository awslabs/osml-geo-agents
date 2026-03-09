# Copyright 2025-2026 Amazon.com, Inc. or its affiliates.

"""Lambda handler for GeoAgent integration tests using pytest."""

from typing import Any, Dict

import pytest

from .integration.test_config import _resolve_mcp_endpoint
from .processor_base import ProcessorBase
from .utils.logger import logger


class TestResultCollector:
    """Simple pytest plugin to collect test results in memory."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.total = 0

    def pytest_runtest_logreport(self, report):
        """Called for each test phase (setup, call, teardown)."""
        # Only count the 'call' phase to avoid triple counting
        if report.when == "call":
            self.total += 1
            if report.passed:
                self.passed += 1
            elif report.failed:
                self.failed += 1
            elif report.skipped:
                self.skipped += 1


class GeoAgentTestProcessor(ProcessorBase):
    """Processor for running GeoAgent integration tests in Lambda using pytest."""

    def __init__(self, event: Dict[str, Any]):
        """
        Initialize the processor with the Lambda event.

        :param event: The Lambda event dictionary (currently unused but available for future test parameters)
        """
        # Get configuration from environment variables (supports both direct
        # values and SSM parameter resolution for stack decoupling)
        mcp_endpoint = _resolve_mcp_endpoint()

        # Store for logging purposes
        self.mcp_endpoint = mcp_endpoint

    def process_sync(self) -> Dict[str, Any]:
        """
        Process the test execution using pytest synchronously.

        This method must be synchronous to avoid event loop conflicts with pytest-asyncio.
        Pytest output flows naturally to stdout, which Lambda captures to CloudWatch.

        :returns: A response indicating the status of the test execution
        """
        logger.info("Running integration tests with pytest")
        logger.info(f"MCP Endpoint: {self.mcp_endpoint}")

        # Create result collector plugin
        collector = TestResultCollector()

        # Run pytest with our collector plugin - output goes directly to CloudWatch via Lambda stdout
        exit_code = pytest.main(
            [
                "-vv",  # Extra verbose output - shows more detail in summary
                "--tb=long",  # Full traceback format - shows complete assertion details
                "--log-cli-level=INFO",  # Show INFO level logs from tests
                "-p",
                "no:cacheprovider",  # Disable cache for Lambda environment
                "-p",
                "pytest_asyncio",  # Explicitly load pytest-asyncio plugin
                "-o",
                "asyncio_mode=auto",  # Enable auto async mode
                "test/integration/test_geo_agents.py",  # Test file path
            ],
            plugins=[collector],
        )

        # Calculate success percentage
        success_pct = (collector.passed / collector.total * 100) if collector.total > 0 else 0.0

        # Log test summary for shell script parsing
        logger.info("\nTest Summary\n-------------------------------------")
        logger.info(
            f"    Tests: {collector.total}, Passed: {collector.passed}, Failed: {collector.failed}, Success: {success_pct:.2f}%"
        )

        if exit_code == 0:
            return self.success_message(f"All {collector.total} integration tests passed")
        else:
            return self.failure_message(Exception(f"{collector.failed} of {collector.total} integration tests failed"))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    The AWS Lambda handler function to execute integration tests.

    :param event: The event payload (can contain test parameters)
    :param context: The Lambda execution context (unused)
    :return: The response from the GeoAgentTestProcessor
    """
    processor = GeoAgentTestProcessor(event)
    return processor.process_sync()
