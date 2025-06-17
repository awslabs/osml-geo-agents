#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import unittest
from unittest.mock import Mock, patch

from aws.osml.geoagents.bedrock import CombineTool, ToolExecutionError
from aws.osml.geoagents.common import Workspace


class TestCombineTool(unittest.TestCase):
    """
    Unit tests for the CombineTool class.

    These tests focus on testing the functionality in combine_tool.py by mocking out
    the combine_operation function. This ensures we're only testing the tool's handling
    of parameters and responses, not the actual combination operation.
    """

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.handler = CombineTool()
        self.mock_workspace = Mock(spec=Workspace)

        # Create a sample event with two geometries and an operation type
        self.event = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-COMBINE",
            "parameters": [
                {"name": "geometry1", "value": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", "type": "string"},
                {"name": "geometry2", "value": "POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))", "type": "string"},
                {"name": "operation", "value": "union", "type": "string"},
            ],
        }

    def test_init(self):
        """Test that the constructor properly initializes the action group and function name."""
        self.assertEqual(self.handler.action_group, "GeoGeometryOperations")
        self.assertEqual(self.handler.function_name, "OSML-GEO-COMBINE")

    @patch("aws.osml.geoagents.bedrock.combine_tool.combine_operation")
    def test_handler_successful_combine(self, mock_combine_operation):
        """Test successful combination of geometries with mocked operation."""
        # Set up the mock to return a predefined result
        expected_result = (
            "The union of the input geometries has been calculated. "
            "Result: POLYGON((0 0, 0 1, 0.5 1, 0.5 1.5, 1.5 1.5, 1.5 0.5, 1 0.5, 1 0, 0 0))"
        )
        mock_combine_operation.return_value = expected_result

        # Call the handler with the event data
        result = self.handler.handler(self.event, None, self.mock_workspace)

        # Verify the mock was called with correct parameters
        mock_combine_operation.assert_called_once()
        args, _ = mock_combine_operation.call_args
        self.assertEqual(len(args), 3)
        self.assertEqual(args[2], "union")  # Check operation parameter

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "")

        # Verify the result structure and content
        self.assertIn(expected_result, result_text)
        self.assertNotIn("isError", result_text)

    @patch("aws.osml.geoagents.bedrock.combine_tool.combine_operation")
    def test_handler_passes_correct_parameters(self, mock_combine_operation):
        """Test that parameters are correctly parsed and passed to combine_operation."""
        # Set up the mock
        mock_combine_operation.return_value = "Mock result"

        # Call the handler
        self.handler.handler(self.event, None, self.mock_workspace)

        # Verify combine_operation was called with correct parameters
        mock_combine_operation.assert_called_once()
        args, _ = mock_combine_operation.call_args

        # Check that the parameters are passed correctly
        self.assertEqual(len(args), 3)
        self.assertEqual(args[2], "union")  # Operation type should be passed as is

    @patch("aws.osml.geoagents.bedrock.combine_tool.combine_operation")
    def test_handler_error_handling(self, mock_combine_operation):
        """Test error handling when combine_operation raises an exception."""
        # Set up the mock to raise an exception
        mock_combine_operation.side_effect = ValueError("Invalid operation type")

        # Call the handler and expect a ToolExecutionError
        with self.assertRaises(ToolExecutionError) as context:
            self.handler.handler(self.event, None, self.mock_workspace)

        # Verify the error message
        self.assertIn("Invalid operation type", str(context.exception))

    def test_missing_required_parameters(self):
        """Test error handling when required parameters are missing."""
        # Test missing geometry1
        event_missing_geometry1 = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-COMBINE",
            "parameters": [
                {"name": "geometry2", "value": "POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))", "type": "string"},
                {"name": "operation", "value": "union", "type": "string"},
            ],
        }
        with self.assertRaises(ToolExecutionError):
            self.handler.handler(event_missing_geometry1, None, self.mock_workspace)

        # Test missing geometry2
        event_missing_geometry2 = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-COMBINE",
            "parameters": [
                {"name": "geometry1", "value": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", "type": "string"},
                {"name": "operation", "value": "union", "type": "string"},
            ],
        }
        with self.assertRaises(ToolExecutionError):
            self.handler.handler(event_missing_geometry2, None, self.mock_workspace)

        # Test missing operation
        event_missing_operation = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-COMBINE",
            "parameters": [
                {"name": "geometry1", "value": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", "type": "string"},
                {"name": "geometry2", "value": "POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))", "type": "string"},
            ],
        }
        with self.assertRaises(ToolExecutionError):
            self.handler.handler(event_missing_operation, None, self.mock_workspace)


if __name__ == "__main__":
    unittest.main()
