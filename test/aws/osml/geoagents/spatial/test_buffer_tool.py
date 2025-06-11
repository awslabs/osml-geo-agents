#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import unittest
from unittest.mock import Mock, patch

from aws.osml.geoagents.common import ToolExecutionError, Workspace
from aws.osml.geoagents.spatial.buffer_tool import BufferTool


class TestBufferTool(unittest.TestCase):
    """
    Unit tests for the BufferTool class.

    These tests focus on testing the functionality in buffer_tool.py by mocking out
    the buffer_operation function. This ensures we're only testing the tool's handling
    of parameters and responses, not the actual buffering operation.
    """

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.handler = BufferTool()
        self.mock_workspace = Mock(spec=Workspace)

        # Create a sample event with a point geometry and distance
        self.event = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-BUFFER",
            "parameters": [
                {"name": "geometry", "value": "POINT(0 0)", "type": "string"},
                {"name": "distance", "value": "1000", "type": "string"},
            ],
        }

    def test_init(self):
        """Test that the constructor properly initializes the action group and function name."""
        self.assertEqual(self.handler.action_group, "GeoGeometryOperations")
        self.assertEqual(self.handler.function_name, "OSML-GEO-BUFFER")

    @patch("aws.osml.geoagents.spatial.buffer_tool.buffer_operation")
    def test_handler_successful_buffer(self, mock_buffer_operation):
        """Test successful buffering of a geometry with mocked operation."""
        # Set up the mock to return a predefined result
        expected_result = "The input geometry has been buffered by 1000 meters. Result: POLYGON ((...))"
        mock_buffer_operation.return_value = expected_result

        # Call the handler with the event data
        result = self.handler.handler(self.event, None, self.mock_workspace)

        # Verify the mock was called with correct parameters
        mock_buffer_operation.assert_called_once()
        args, _ = mock_buffer_operation.call_args
        self.assertEqual(len(args), 2)
        self.assertEqual(args[1], 1000.0)  # Check distance parameter

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "")

        # Verify the result structure and content
        self.assertIn(expected_result, result_text)
        self.assertNotIn("isError", result_text)

    @patch("aws.osml.geoagents.spatial.buffer_tool.buffer_operation")
    def test_handler_passes_correct_parameters(self, mock_buffer_operation):
        """Test that parameters are correctly parsed and passed to buffer_operation."""
        # Set up the mock
        mock_buffer_operation.return_value = "Mock result"

        # Call the handler
        self.handler.handler(self.event, None, self.mock_workspace)

        # Verify buffer_operation was called with correct parameters
        mock_buffer_operation.assert_called_once()
        args, _ = mock_buffer_operation.call_args

        # Check that the first argument is the geometry and second is the distance
        self.assertEqual(len(args), 2)
        self.assertEqual(args[1], 1000.0)  # Distance should be converted to float

    @patch("aws.osml.geoagents.spatial.buffer_tool.buffer_operation")
    def test_handler_error_handling(self, mock_buffer_operation):
        """Test error handling when buffer_operation raises an exception."""
        # Set up the mock to raise an exception
        mock_buffer_operation.side_effect = ValueError("Invalid geometry")

        # Call the handler and expect a ToolExecutionError
        with self.assertRaises(ToolExecutionError) as context:
            self.handler.handler(self.event, None, self.mock_workspace)

        # Verify the error message
        self.assertIn("Unable to buffer the geometry", str(context.exception))
        self.assertIn("Invalid geometry", str(context.exception))

    def test_missing_required_parameters(self):
        """Test error handling when required parameters are missing."""
        # Test missing geometry
        event_missing_geometry = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-BUFFER",
            "parameters": [
                {"name": "distance", "value": "100", "type": "string"},
            ],
        }
        with self.assertRaises(ToolExecutionError) as context:
            self.handler.handler(event_missing_geometry, None, self.mock_workspace)
        self.assertIn("Missing required parameter", str(context.exception))

        # Test missing distance
        event_missing_distance = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-BUFFER",
            "parameters": [
                {"name": "geometry", "value": "POINT(0 0)", "type": "string"},
            ],
        }
        with self.assertRaises(ToolExecutionError) as context:
            self.handler.handler(event_missing_distance, None, self.mock_workspace)
        self.assertIn("Missing required parameter", str(context.exception))

    @patch("aws.osml.geoagents.spatial.buffer_tool.buffer_operation")
    def test_invalid_distance_parameter(self, mock_buffer_operation):
        """Test error handling when distance parameter is invalid."""
        # Create an event with invalid distance
        event_invalid_distance = {
            "agent": "test_agent",
            "actionGroup": "GeoGeometryOperations",
            "function": "OSML-GEO-BUFFER",
            "parameters": [
                {"name": "geometry", "value": "POINT(0 0)", "type": "string"},
                {"name": "distance", "value": "not_a_number", "type": "string"},
            ],
        }

        # Call the handler and expect a ToolExecutionError
        with self.assertRaises(ToolExecutionError) as context:
            self.handler.handler(event_invalid_distance, None, self.mock_workspace)
        self.assertIn("Unable to parse", str(context.exception))


if __name__ == "__main__":
    unittest.main()
