#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aws.osml.geoagents.bedrock import CorrelationTool, ToolExecutionError
from aws.osml.geoagents.common import GeoDataReference, Workspace
from aws.osml.geoagents.spatial import CorrelationTypes


class TestCorrelationTool(unittest.TestCase):
    """Test cases for the Correlation Tool."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.tool = CorrelationTool()
        self.mock_workspace = MagicMock(spec=Workspace)
        self.mock_workspace.session_local_path = Path("/tmp/osml-geo-agents/test")
        self.context = {}

        # Create a sample event with required parameters
        self.event = {
            "actionGroup": "SpatialReasoning",
            "function": "CORRELATE",
            "parameters": [
                {"name": "dataset1", "value": "stac:dataset1", "type": "string"},
                {"name": "dataset2", "value": "stac:dataset2", "type": "string"},
                {"name": "correlation_type", "value": "intersection", "type": "string"},
                {"name": "distance", "value": "100", "type": "string"},
            ],
        }

    def test_init(self):
        """Test CorrelationTool initialization."""
        self.assertEqual(self.tool.action_group, "SpatialReasoning")
        self.assertEqual(self.tool.function_name, "CORRELATE")

    @patch("aws.osml.geoagents.bedrock.correlation_tool.correlation_operation")
    def test_handler_with_all_parameters(self, mock_correlation_operation):
        """Test correlation tool handler with all parameters."""
        # Add geometry column parameters to the event
        event_with_geo_columns = self.event.copy()
        event_with_geo_columns["parameters"].extend(
            [
                {"name": "dataset1_geo_column_name", "value": "geometry1", "type": "string"},
                {"name": "dataset2_geo_column_name", "value": "geometry2", "type": "string"},
            ]
        )

        # Mock the correlation_operation function to return a predefined result
        mock_correlation_operation.return_value = (
            "The datasets stac:dataset1 and stac:dataset2 have been correlated using the intersection operation. "
            "The correlated result is known as stac:CORRELATE-20250612. "
            "A summary of the contents is: This dataset contains 3 features resulting from a intersection "
            "correlation operation between stac:dataset1 and stac:dataset2. "
            "A buffer of 100 units was applied to the first dataset."
        )

        # Execute handler
        result = self.tool.handler(event_with_geo_columns, self.context, self.mock_workspace)

        # Verify correlation_operation was called with the correct parameters
        mock_correlation_operation.assert_called_once_with(
            dataset1_georef=GeoDataReference("stac:dataset1"),
            dataset2_georef=GeoDataReference("stac:dataset2"),
            correlation_type=CorrelationTypes.INTERSECTION,
            distance=100.0,
            dataset1_geo_column="geometry1",
            dataset2_geo_column="geometry2",
            workspace=self.mock_workspace,
            function_name=self.tool.function_name,
        )

        # Verify the response contains the mocked result
        self.assertIn("The datasets stac:dataset1 and stac:dataset2 have been correlated", str(result["response"]))
        self.assertIn("intersection operation", str(result["response"]))
        self.assertIn("stac:CORRELATE-20250612", str(result["response"]))

    @patch("aws.osml.geoagents.bedrock.correlation_tool.correlation_operation")
    def test_handler_with_minimal_parameters(self, mock_correlation_operation):
        """Test correlation tool handler with minimal parameters."""
        # Create event with only required parameters
        minimal_event = {
            "actionGroup": "SpatialReasoning",
            "function": "CORRELATE",
            "parameters": [
                {"name": "dataset1", "value": "stac:dataset1", "type": "string"},
                {"name": "dataset2", "value": "stac:dataset2", "type": "string"},
            ],
        }

        # Mock the correlation_operation function to return a predefined result
        mock_correlation_operation.return_value = (
            "The datasets stac:dataset1 and stac:dataset2 have been correlated using the intersection operation. "
            "The correlated result is known as stac:CORRELATE-20250612. "
            "A summary of the contents is: This dataset contains 3 features resulting from a intersection "
            "correlation operation between stac:dataset1 and stac:dataset2."
        )

        # Execute handler
        result = self.tool.handler(minimal_event, self.context, self.mock_workspace)

        # Verify correlation_operation was called with the correct parameters
        mock_correlation_operation.assert_called_once_with(
            dataset1_georef=GeoDataReference("stac:dataset1"),
            dataset2_georef=GeoDataReference("stac:dataset2"),
            correlation_type=None,  # Should be None since not provided
            distance=None,  # Should be None since not provided
            dataset1_geo_column=None,  # Should be None since not provided
            dataset2_geo_column=None,  # Should be None since not provided
            workspace=self.mock_workspace,
            function_name=self.tool.function_name,
        )

        # Verify the response contains the mocked result
        self.assertIn("The datasets stac:dataset1 and stac:dataset2 have been correlated", str(result["response"]))
        self.assertIn("intersection operation", str(result["response"]))

    @patch("aws.osml.geoagents.bedrock.correlation_tool.correlation_operation")
    def test_handler_with_different_correlation_type(self, mock_correlation_operation):
        """Test correlation tool handler with difference correlation type."""
        # Modify event to use difference correlation type
        event_with_difference = self.event.copy()
        for param in event_with_difference["parameters"]:
            if param["name"] == "correlation_type":
                param["value"] = "difference"
                break

        # Mock the correlation_operation function to return a predefined result
        mock_correlation_operation.return_value = (
            "The datasets stac:dataset1 and stac:dataset2 have been correlated using the difference operation. "
            "The correlated result is known as stac:CORRELATE-20250612. "
            "A summary of the contents is: This dataset contains 2 features resulting from a difference "
            "correlation operation between stac:dataset1 and stac:dataset2. "
            "A buffer of 100 units was applied to the first dataset."
        )

        # Execute handler
        result = self.tool.handler(event_with_difference, self.context, self.mock_workspace)

        # Verify correlation_operation was called with the correct parameters
        mock_correlation_operation.assert_called_once_with(
            dataset1_georef=GeoDataReference("stac:dataset1"),
            dataset2_georef=GeoDataReference("stac:dataset2"),
            correlation_type=CorrelationTypes.DIFFERENCE,
            distance=100.0,
            dataset1_geo_column=None,
            dataset2_geo_column=None,
            workspace=self.mock_workspace,
            function_name=self.tool.function_name,
        )

        # Verify the response contains the mocked result
        self.assertIn("The datasets stac:dataset1 and stac:dataset2 have been correlated", str(result["response"]))
        self.assertIn("difference operation", str(result["response"]))

    @patch("aws.osml.geoagents.bedrock.correlation_tool.correlation_operation")
    def test_handler_error_handling(self, mock_correlation_operation):
        """Test error handling when correlation_operation raises an exception."""
        # Mock the correlation_operation function to raise an exception
        mock_correlation_operation.side_effect = ValueError("Test error message")

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(self.event, self.context, self.mock_workspace)

        self.assertIn("Unable to correlate the datasets", str(context.exception))
        self.assertIn("Test error message", str(context.exception))

    def test_missing_dataset1(self):
        """Test that the tool handles missing dataset1 parameter."""
        event = {
            "actionGroup": "SpatialReasoning",
            "function": "CORRELATE",
            "parameters": [
                {"name": "dataset2", "value": "stac:dataset2", "type": "string"},
                {"name": "correlation_type", "value": "intersection", "type": "string"},
            ],
        }

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event, self.context, self.mock_workspace)

        self.assertIn("Missing required parameter: 'dataset1'", str(context.exception))

    def test_missing_dataset2(self):
        """Test that the tool handles missing dataset2 parameter."""
        event = {
            "actionGroup": "SpatialReasoning",
            "function": "CORRELATE",
            "parameters": [
                {"name": "dataset1", "value": "stac:dataset1", "type": "string"},
                {"name": "correlation_type", "value": "intersection", "type": "string"},
            ],
        }

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event, self.context, self.mock_workspace)

        self.assertIn("Missing required parameter: 'dataset2'", str(context.exception))


if __name__ == "__main__":
    unittest.main()
