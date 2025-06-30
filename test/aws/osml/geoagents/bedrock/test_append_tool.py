#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from aws.osml.geoagents.bedrock import AppendTool, ToolExecutionError
from aws.osml.geoagents.common import Georeference, Workspace


class TestAppendTool(unittest.TestCase):
    """
    Unit tests for the AppendTool class.

    These tests verify the functionality of the append tool, including parameter validation,
    append operations, and error handling.
    """

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = AppendTool()
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = Path("/tmp/osml-geo-agents/test")
        self.context = {}

        # Create a sample event with required parameters
        self.event = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "APPEND",
            "parameters": [
                {"name": "datasets", "value": ["georef:dataset1", "georef:dataset2", "georef:dataset3"], "type": "array"},
                {"name": "output_format", "value": "parquet", "type": "string"},
            ],
            "messageVersion": "1.0",
        }

    def test_constructor(self):
        """Test that the constructor properly initializes the action group and function name."""
        self.assertEqual(self.tool.action_group, "SpatialReasoning")
        self.assertEqual(self.tool.function_name, "APPEND")

    @patch("aws.osml.geoagents.bedrock.append_tool.append_operation")
    def test_handler_successful_append(self, mock_append_operation):
        """Test successful append with valid parameters."""
        # Mock the append_operation function to return a predefined result
        mock_append_operation.return_value = (
            "The 3 datasets have been combined into a single dataset. "
            "The combined result is known as georef:APPEND-20250612. "
            "A summary of the contents is: This dataset contains 15 features resulting from appending "
            "3 datasets: Dataset 1, Dataset 2, Dataset 3."
        )

        # Call the handler
        result = self.tool.handler(self.event, self.context, self.mock_workspace)

        # Verify append_operation was called with the correct parameters
        mock_append_operation.assert_called_once_with(
            dataset_georefs=[
                Georeference("georef:dataset1"),
                Georeference("georef:dataset2"),
                Georeference("georef:dataset3"),
            ],
            workspace=self.mock_workspace,
            function_name=self.tool.function_name,
            output_format="parquet",
        )

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "")

        # Verify the result contains information about the append operation
        self.assertIn("3 datasets have been combined", result_text)
        self.assertIn("georef:APPEND-20250612", result_text)
        self.assertIn("15 features", result_text)

    @patch("aws.osml.geoagents.bedrock.append_tool.append_operation")
    def test_handler_with_default_output_format(self, mock_append_operation):
        """Test append with default output format when not specified."""
        # Create event without output_format parameter
        event_no_format = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "APPEND",
            "parameters": [
                {"name": "datasets", "value": ["georef:dataset1", "georef:dataset2"], "type": "array"},
            ],
            "messageVersion": "1.0",
        }

        # Mock the append_operation function to return a predefined result
        mock_append_operation.return_value = (
            "The 2 datasets have been combined into a single dataset. "
            "The combined result is known as georef:APPEND-20250612."
        )

        # Call the handler
        result = self.tool.handler(event_no_format, self.context, self.mock_workspace)

        # Verify append_operation was called with the default output_format
        mock_append_operation.assert_called_once_with(
            dataset_georefs=[Georeference("georef:dataset1"), Georeference("georef:dataset2")],
            workspace=self.mock_workspace,
            function_name=self.tool.function_name,
            output_format="parquet",  # Default value
        )

        # Parse the result
        result_body = json.loads(result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"])
        result_text = result_body.get("result", "")

        # Verify the result contains information about the append operation
        self.assertIn("2 datasets have been combined", result_text)

    def test_handler_missing_datasets_parameter(self):
        """Test handling of missing datasets parameter."""
        # Create event with missing datasets parameter
        event_missing_param = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "APPEND",
            "parameters": [
                {"name": "output_format", "value": "parquet", "type": "string"},
                # datasets parameter is missing
            ],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_missing_param, self.context, self.mock_workspace)

        # Verify the error message
        self.assertIn("Missing required parameter", str(context.exception))
        self.assertIn("datasets", str(context.exception))

    def test_handler_invalid_datasets_parameter_type(self):
        """Test handling of invalid datasets parameter type."""
        # Create event with invalid datasets parameter (not a list)
        event_invalid_param = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "APPEND",
            "parameters": [
                {"name": "datasets", "value": "not_a_list", "type": "string"},
            ],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_invalid_param, self.context, self.mock_workspace)

        # Verify the error message
        self.assertIn("Unable to parse 'datasets' parameter", str(context.exception))
        self.assertIn("must be a list", str(context.exception))

    def test_handler_invalid_dataset_reference(self):
        """Test handling of invalid dataset reference in the list."""
        # Create event with an invalid dataset reference
        event_invalid_ref = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "APPEND",
            "parameters": [
                {"name": "datasets", "value": ["georef:valid", 123, "georef:also_valid"], "type": "array"},
            ],
        }

        # We expect a ToolExecutionError because 123 is not a valid georeference
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_invalid_ref, self.context, self.mock_workspace)

        # Verify the error message
        self.assertIn("Unable to parse 'datasets' parameter", str(context.exception))
        self.assertIn("123", str(context.exception))

    def test_handler_invalid_output_format(self):
        """Test handling of invalid output format."""
        # Create event with invalid output format
        event_invalid_format = {
            "agent": "test_agent",
            "actionGroup": "SpatialReasoning",
            "function": "APPEND",
            "parameters": [
                {"name": "datasets", "value": ["georef:dataset1", "georef:dataset2"], "type": "array"},
                {"name": "output_format", "value": "invalid_format", "type": "string"},
            ],
        }

        # Call the handler and expect an exception
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_invalid_format, self.context, self.mock_workspace)

        # Verify the error message
        self.assertIn("Invalid output_format", str(context.exception))
        self.assertIn("Must be one of: 'parquet', 'geojson'", str(context.exception))

    @patch("aws.osml.geoagents.bedrock.append_tool.append_operation")
    def test_handler_error_handling(self, mock_append_operation):
        """Test error handling when append_operation raises an exception."""
        # Mock the append_operation function to raise an exception
        mock_append_operation.side_effect = ValueError("Test error message")

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, self.context, self.mock_workspace)

        # Verify the error message contains both the prefix and the original error
        error_message = str(context.exception)
        self.assertIn("Unable to append the datasets", error_message)
        self.assertIn("Test error message", error_message)


if __name__ == "__main__":
    unittest.main()
