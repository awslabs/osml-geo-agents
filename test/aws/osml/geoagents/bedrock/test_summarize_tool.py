#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from unittest.mock import Mock, patch

from aws.osml.geoagents.bedrock import SummarizeTool, ToolExecutionError
from aws.osml.geoagents.common import GeoDataReference, Workspace


class TestSummarizeTool(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = SummarizeTool()
        self.workspace = Mock(spec=Workspace)

        # Create a basic event structure for testing
        self.event = {
            "actionGroup": "SpatialReasoning",
            "function": "SUMMARIZE",
            "parameters": [{"name": "dataset", "value": "stac:test-dataset"}],
        }

        # Create a basic context structure for testing
        self.context = {}

    def test_init(self):
        """Test SummarizeTool initialization."""
        self.assertEqual(self.tool.action_group, "SpatialReasoning")
        self.assertEqual(self.tool.function_name, "SUMMARIZE")

    def test_missing_dataset_parameter(self):
        """Test error handling when the dataset parameter is missing."""
        # Create an event with no parameters
        event_missing_param = {"actionGroup": "SpatialReasoning", "function": "SUMMARIZE", "parameters": []}

        # Assert that the handler raises a ToolExecutionError
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event_missing_param, self.context, self.workspace)

        # Check the error message
        self.assertIn("Missing required parameter: 'dataset'", str(context.exception))

    @patch("aws.osml.geoagents.bedrock.CommonParameters.parse_dataset_georef")
    def test_none_dataset_parameter(self, mock_parse_dataset_georef):
        """Test error handling when the dataset parameter is parsed as None."""
        # Make the parse_dataset_georef method return None
        mock_parse_dataset_georef.return_value = None

        # Assert that the handler raises a ToolExecutionError
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, self.context, self.workspace)

        # Check the error message
        self.assertIn("Missing required parameter: 'dataset'", str(context.exception))

    @patch("aws.osml.geoagents.bedrock.CommonParameters.parse_dataset_georef")
    @patch("aws.osml.geoagents.bedrock.summarize_tool.summarize_operation")
    def test_tool_execution_error_from_operation(self, mock_summarize_operation, mock_parse_dataset_georef):
        """Test handling of ToolExecutionError from the summarize operation."""
        # Set up the mock to return a valid GeoDataReference
        mock_georef = Mock(spec=GeoDataReference)
        mock_parse_dataset_georef.return_value = mock_georef

        # Make the summarize_operation raise a ToolExecutionError
        error_message = "Test operation error"
        mock_summarize_operation.side_effect = ToolExecutionError(error_message)

        # Assert that the handler raises a ToolExecutionError
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, self.context, self.workspace)

        # Check the error message
        self.assertEqual(error_message, str(context.exception))

    @patch("aws.osml.geoagents.bedrock.CommonParameters.parse_dataset_georef")
    @patch("aws.osml.geoagents.bedrock.summarize_tool.summarize_operation")
    def test_generic_exception_from_operation(self, mock_summarize_operation, mock_parse_dataset_georef):
        """Test handling of generic exceptions from the summarize operation."""
        # Set up the mock to return a valid GeoDataReference
        mock_georef = Mock(spec=GeoDataReference)
        mock_parse_dataset_georef.return_value = mock_georef

        # Make the summarize_operation raise a generic Exception
        error_message = "Unexpected error"
        mock_summarize_operation.side_effect = Exception(error_message)

        # Assert that the handler raises a ToolExecutionError
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, self.context, self.workspace)

        # Check the error message contains the original exception message
        self.assertIn(error_message, str(context.exception))
        self.assertIn("Unable to summarize the dataset", str(context.exception))

    @patch("aws.osml.geoagents.bedrock.CommonParameters.parse_dataset_georef")
    @patch("aws.osml.geoagents.bedrock.summarize_tool.summarize_operation")
    def test_value_error_from_operation(self, mock_summarize_operation, mock_parse_dataset_georef):
        """Test handling of ValueError from the summarize operation."""
        # Set up the mock to return a valid GeoDataReference
        mock_georef = Mock(spec=GeoDataReference)
        mock_parse_dataset_georef.return_value = mock_georef

        # Make the summarize_operation raise a ValueError
        error_message = "Invalid value"
        mock_summarize_operation.side_effect = ValueError(error_message)

        # Assert that the handler raises a ToolExecutionError
        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, self.context, self.workspace)

        # Check the error message contains the original exception message
        self.assertIn(error_message, str(context.exception))
        self.assertIn("Unable to summarize the dataset", str(context.exception))


if __name__ == "__main__":
    unittest.main()
