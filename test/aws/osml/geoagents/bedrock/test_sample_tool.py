#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aws.osml.geoagents.bedrock import SampleTool, ToolExecutionError
from aws.osml.geoagents.common import GeoDataReference, Workspace


class TestSampleTool(unittest.TestCase):
    """Test cases for the Sample Tool."""

    def setUp(self):
        """Set up test fixtures."""
        self.tool = SampleTool()
        self.workspace = MagicMock(spec=Workspace)
        self.workspace.session_local_path = Path("/tmp/test")
        self.context = {}

    def test_sample_tool_init(self):
        """Test that the tool initializes with correct action group and function name."""
        self.assertEqual(self.tool.action_group, "SpatialReasoning")
        self.assertEqual(self.tool.function_name, "SAMPLE")

    @patch("aws.osml.geoagents.bedrock.sample_tool.sample_operation")
    def test_sample_features_success(self, mock_sample_operation):
        """Test successful sampling of features from a dataset."""
        # Mock the sample_operation function to return a predefined result
        mock_sample_operation.return_value = (
            "Sample of 2 features from test-dataset:\nFeature 1: Test Feature\nFeature 2: Another Feature"
        )

        # Test with explicit number of features
        event = {
            "actionGroup": "SpatialReasoning",
            "function": "SAMPLE",
            "parameters": [
                {"name": "dataset", "value": "stac:test-dataset", "type": "string"},
                {"name": "number_of_features", "value": "2", "type": "number"},
            ],
        }

        result = self.tool.handler(event, self.context, self.workspace)

        # Verify sample_operation was called with the correct parameters
        mock_sample_operation.assert_called_once_with(
            dataset_reference=GeoDataReference("stac:test-dataset"), number_of_features=2, workspace=self.workspace
        )

        # Verify the response contains the mocked result
        self.assertIn("Sample of 2 features from test-dataset", str(result["response"]))

    @patch("aws.osml.geoagents.bedrock.sample_tool.sample_operation")
    def test_sample_features_default_number(self, mock_sample_operation):
        """Test sampling features with default number of features."""
        # Mock the sample_operation function to return a predefined result
        mock_sample_operation.return_value = "Sample of 10 features from test-dataset:\nFeature details..."

        # Test without specifying number_of_features
        event = {
            "actionGroup": "SpatialReasoning",
            "function": "SAMPLE",
            "parameters": [
                {"name": "dataset", "value": "stac:test-dataset", "type": "string"},
            ],
        }

        result = self.tool.handler(event, self.context, self.workspace)

        # Verify sample_operation was called with None for number_of_features
        mock_sample_operation.assert_called_once_with(
            dataset_reference=GeoDataReference("stac:test-dataset"), number_of_features=None, workspace=self.workspace
        )

        # Verify the response contains the mocked result
        self.assertIn("Sample of 10 features from test-dataset", str(result["response"]))

    def test_missing_dataset(self):
        """Test that the tool handles missing dataset parameter."""
        event = {
            "actionGroup": "SpatialReasoning",
            "function": "SAMPLE",
            "parameters": [{"name": "number_of_features", "value": "5"}],
        }

        with self.assertRaises(ToolExecutionError) as context:
            self.tool.handler(event, self.context, self.workspace)

        self.assertIn("Missing required parameter: 'dataset'", str(context.exception))


if __name__ == "__main__":
    unittest.main()
