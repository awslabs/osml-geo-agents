#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import unittest
from unittest.mock import Mock, patch

from aws.osml.geoagents.bedrock import ToolExecutionError, TranslateTool
from aws.osml.geoagents.common import Workspace


class TestTranslateTool(unittest.TestCase):
    """
    Unit tests for the TranslateTool class.

    These tests focus on testing the functionality in translate_tool.py by mocking out
    the translate_operation function. This ensures we're only testing the tool's handling
    of parameters and responses, not the actual translation operation.
    """

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.handler = TranslateTool()
        self.mock_workspace = Mock(spec=Workspace)

        # Create a sample event with a point geometry, distance, and heading
        self.event = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-MOVE",
            "parameters": [
                {"name": "shape", "value": "POINT(0 0)", "type": "string"},
                {"name": "distance", "value": "1000", "type": "string"},
                {"name": "heading", "value": "90", "type": "string"},
            ],
        }

    def test_init(self):
        """Test that the constructor properly initializes the action group and function name."""
        self.assertEqual(self.handler.action_group, "GeoGeometryOperations")
        self.assertEqual(self.handler.function_name, "OSML-GEO-MOVE")

    @patch("aws.osml.geoagents.bedrock.translate_tool.translate_operation")
    def test_handler_successful_translate(self, mock_translate_operation):
        """Test successful translation of a geometry with mocked operation."""
        # Set up the mock to return a predefined result
        expected_result = (
            "The input geometry has been translated by 1000 meters at heading 90 degrees. Result: POINT (0.01 0)"
        )
        mock_translate_operation.return_value = expected_result

        # Call the handler with the event data
        result = self.handler.handler(self.event, None, self.mock_workspace)

        # Verify the mock was called with correct parameters
        mock_translate_operation.assert_called_once()
        args, _ = mock_translate_operation.call_args
        self.assertEqual(len(args), 3)
        self.assertEqual(args[1], 1000.0)  # Check distance parameter
        self.assertEqual(args[2], 90.0)  # Check heading parameter

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "")

        # Verify the result structure and content
        self.assertIn(expected_result, result_text)
        self.assertNotIn("isError", result_text)

    @patch("aws.osml.geoagents.bedrock.translate_tool.translate_operation")
    def test_handler_passes_correct_parameters(self, mock_translate_operation):
        """Test that parameters are correctly parsed and passed to translate_operation."""
        # Set up the mock
        mock_translate_operation.return_value = "Mock result"

        # Call the handler
        self.handler.handler(self.event, None, self.mock_workspace)

        # Verify translate_operation was called with correct parameters
        mock_translate_operation.assert_called_once()
        args, _ = mock_translate_operation.call_args

        # Check that the parameters are passed correctly
        self.assertEqual(len(args), 3)
        self.assertEqual(args[1], 1000.0)  # Distance should be converted to float
        self.assertEqual(args[2], 90.0)  # Heading should be converted to float

    @patch("aws.osml.geoagents.bedrock.translate_tool.translate_operation")
    def test_handler_error_handling(self, mock_translate_operation):
        """Test error handling when translate_operation raises an exception."""
        # Set up the mock to raise an exception
        mock_translate_operation.side_effect = ValueError("Invalid heading")

        # Call the handler and expect a ToolExecutionError
        with self.assertRaises(ToolExecutionError) as context:
            self.handler.handler(self.event, None, self.mock_workspace)

        # Verify the error message
        self.assertIn("Invalid heading", str(context.exception))

    def test_missing_required_parameters(self):
        """Test error handling when required parameters are missing."""
        # Test missing shape
        event_missing_shape = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-MOVE",
            "parameters": [
                {"name": "distance", "value": "1000", "type": "string"},
                {"name": "heading", "value": "90", "type": "string"},
            ],
        }
        with self.assertRaises(ToolExecutionError):
            self.handler.handler(event_missing_shape, None, self.mock_workspace)

        # Test missing distance
        event_missing_distance = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-MOVE",
            "parameters": [
                {"name": "shape", "value": "POINT(0 0)", "type": "string"},
                {"name": "heading", "value": "90", "type": "string"},
            ],
        }
        with self.assertRaises(ToolExecutionError):
            self.handler.handler(event_missing_distance, None, self.mock_workspace)

        # Test missing heading
        event_missing_heading = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-MOVE",
            "parameters": [
                {"name": "shape", "value": "POINT(0 0)", "type": "string"},
                {"name": "distance", "value": "1000", "type": "string"},
            ],
        }
        with self.assertRaises(ToolExecutionError):
            self.handler.handler(event_missing_heading, None, self.mock_workspace)


if __name__ == "__main__":
    unittest.main()
