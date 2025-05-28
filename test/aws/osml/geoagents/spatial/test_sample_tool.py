#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pystac

from aws.osml.geoagents.common import ToolExecutionError, Workspace
from aws.osml.geoagents.spatial.sample_tool import SampleTool


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

    @patch("aws.osml.geoagents.spatial.sample_tool.read_geo_data_frame")
    def test_sample_features_success(self, mock_read_gdf):
        """Test successful sampling of features from a dataset."""
        # Create a mock geodataframe with some test data
        test_data = {
            "id": [1, 2, 3],
            "name": ["Feature-A", "Feature-B", "Feature-C"],
            "geometry": [None, None, None],  # Simplified for testing
        }
        mock_gdf = gpd.GeoDataFrame(pd.DataFrame(test_data))
        mock_read_gdf.return_value = mock_gdf

        # Create a mock STAC item
        mock_item = pystac.Item(
            id="test-item",
            geometry=None,
            bbox=None,
            datetime=datetime.fromisoformat("2025-04-23T14:05:23Z"),
            properties={"title": "Test Dataset"},
        )

        # Set up the mock workspace context manager
        self.workspace.get_item.return_value = mock_item
        mock_local_assets = {"data": Path("/tmp/test/data.parquet")}

        with patch("aws.osml.geoagents.spatial.sample_tool.LocalAssets") as mock_local_assets_cm:
            mock_local_assets_cm.return_value.__enter__.return_value = (mock_item, mock_local_assets)

            # Test with explicit number of features
            event = {
                "actionGroup": "SpatialReasoning",
                "function": "SAMPLE",
                "parameters": [
                    {"name": "dataset", "value": "georef:test-dataset", "type": "string"},
                    {"name": "number_of_features", "value": "2", "type": "number"},
                ],
            }

            result = self.tool.handler(event, self.context, self.workspace)

            # Verify the response contains expected information
            response_str = str(result["response"])
            self.assertIn("Sample of 2 features", response_str)
            self.assertIn("Feature-A", response_str)
            self.assertIn("Feature-B", response_str)
            self.assertNotIn("Feature-C", response_str)

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
