#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

from aws.osml.geoagents.bedrock import FilterTool, ToolExecutionError
from aws.osml.geoagents.common import GeoDataReference, Workspace


class TestFilterTool(unittest.TestCase):
    """Test cases for the Filter Tool."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = FilterTool()
        self.mock_workspace = MagicMock(spec=Workspace)
        self.mock_workspace.session_local_path = Path("/tmp/osml-geo-agents/test")
        self.context = {}

        # Create a sample event
        self.event = {
            "actionGroup": "SpatialReasoning",
            "function": "FILTER",
            "parameters": [
                {"name": "dataset", "value": "stac:test-dataset", "type": "string"},
                {"name": "filter", "value": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", "type": "string"},
            ],
        }

    def test_filter_tool_init(self):
        """Test that the tool initializes with correct action group and function name."""
        self.assertEqual(self.tool.action_group, "SpatialReasoning")
        self.assertEqual(self.tool.function_name, "FILTER")

    @patch("aws.osml.geoagents.bedrock.filter_tool.filter_operation")
    def test_filter_features_success(self, mock_filter_operation):
        """Test successful filtering of features from a dataset."""
        # Mock the filter_operation function to return a predefined result
        mock_filter_operation.return_value = (
            "The dataset stac:test-dataset has been filtered. "
            "The filtered result is known as stac:FILTER-20250612. "
            "A summary of the contents is: This dataset contains 5 features selected from "
            "stac:test-dataset because they were within the boundary of POLYGON((0 0, 1 0, 1 1, 0 1, 0 0)). "
        )

        result = self.tool.handler(self.event, self.context, self.mock_workspace)

        # Verify filter_operation was called with the correct parameters
        mock_filter_operation.assert_called_once_with(
            dataset_reference=GeoDataReference("stac:test-dataset"),
            filter_reference=GeoDataReference("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"),
            filter_type=ANY,  # Using ANY since we can't easily compare enum values
            dataset_geo_column=None,
            filter_geo_column=None,
            workspace=self.mock_workspace,
            function_name=self.tool.function_name,
        )

        # Verify the response contains the mocked result
        self.assertIn("The dataset stac:test-dataset has been filtered", str(result["response"]))
        self.assertIn("stac:FILTER-20250612", str(result["response"]))

    @patch("aws.osml.geoagents.bedrock.filter_tool.filter_operation")
    def test_filter_features_error_handling(self, mock_filter_operation):
        """Test error handling when filter_operation raises an exception."""
        # Mock the filter_operation function to raise an exception
        mock_filter_operation.side_effect = ValueError("Test error message")

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, self.context, self.mock_workspace)

        self.assertIn("Unable to filter the dataset", str(context.exception))
        self.assertIn("Test error message", str(context.exception))

    def test_missing_dataset(self):
        """Test that the tool handles missing dataset parameter."""
        event = {
            "actionGroup": "SpatialReasoning",
            "function": "FILTER",
            "parameters": [
                {"name": "filter", "value": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", "type": "string"},
            ],
        }

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event, self.context, self.mock_workspace)

        self.assertIn("Missing required parameter: 'dataset'", str(context.exception))

    def test_missing_filter(self):
        """Test that the tool handles missing filter parameter."""
        event = {
            "actionGroup": "SpatialReasoning",
            "function": "FILTER",
            "parameters": [
                {"name": "dataset", "value": "stac:test-dataset", "type": "string"},
            ],
        }

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event, self.context, self.mock_workspace)

        self.assertIn("Missing required parameter: 'filter'", str(context.exception))


if __name__ == "__main__":
    unittest.main()
