#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
import shapely
from pystac import Asset, Item

from aws.osml.geoagents.common import Workspace
from aws.osml.geoagents.spatial.filter_tool import FilterTool


class TestFilterTool(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.handler = FilterTool()
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = Path("/tmp/osml-geo-agents/test")

        # Create a sample event
        self.event = {
            "agent": "test_agent",
            "actionGroup": "test_group",
            "function": "Filter",
            "parameters": [
                {"name": "dataset", "value": "georef:1234", "type": "string"},
                {"name": "filter", "value": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", "type": "string"},
            ],
        }

        # Create a sample STAC item
        self.sample_item = Item(
            id="georef:1234",
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]},
            datetime=datetime.fromisoformat("2025-04-23T14:05:23Z"),
            bbox=[0, 0, 2, 2],
            properties={
                "title": "Test Dataset",
                "keywords": ["test"],
            },
            assets={"data": Asset(href="s3://fake-test-bucket/data.parquet")},
        )

    def test_handler_successful_filter(self):
        """Test successful filtering of a dataset."""
        # Mock the workspace methods
        self.mock_workspace.get_item.return_value = self.sample_item
        self.mock_workspace.download_assets.return_value = {"data": Path("/tmp/test/sample.geojson")}
        self.mock_workspace.publish_item = Mock()

        # Create sample GeoDataFrame for testing
        sample_gdf = gpd.GeoDataFrame({"geometry": [shapely.geometry.Point(0.5, 0.5), shapely.geometry.Point(1.5, 1.5)]})

        # Mock GeoDataFrame.from_file
        with patch("geopandas.GeoDataFrame.from_file", return_value=sample_gdf):
            result = self.handler.handler(self.event, None, self.mock_workspace)

        # Verify the result
        self.assertIn("has been filtered", str(result))
        self.assertIn("georef:", str(result))

        # Verify workspace interactions
        self.mock_workspace.get_item.assert_called_once()
        self.mock_workspace.download_assets.assert_called_once()
        self.mock_workspace.publish_item.assert_called_once()

    def test_empty_filter_result(self):
        """Test handling of filter that results in empty dataset."""
        self.mock_workspace.get_item.return_value = self.sample_item
        self.mock_workspace.download_assets.return_value = {"data": Path("/tmp/test/sample.geojson")}

        # Create empty GeoDataFrame for testing
        empty_gdf = gpd.GeoDataFrame({"geometry": []})

        # Mock GeoDataFrame.from_file
        with patch("geopandas.GeoDataFrame.from_file", return_value=empty_gdf):
            result = self.handler.handler(self.event, None, self.mock_workspace)

        # Verify the result indicates empty dataset
        self.assertIn("0 features", str(result).lower())


if __name__ == "__main__":
    unittest.main()
