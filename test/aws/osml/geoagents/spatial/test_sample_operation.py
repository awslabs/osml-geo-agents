#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from unittest.mock import Mock, patch

import geopandas as gpd
import shapely

from aws.osml.geoagents.common import Georeference, Workspace
from aws.osml.geoagents.spatial.sample_operation import sample_operation


class TestSampleOperation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock workspace
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = "/tmp"

        # Create a mock georeference
        self.dataset_georef = Mock(spec=Georeference)

        # Create mock number of features
        self.number_of_features = 3

    @patch("aws.osml.geoagents.spatial.sample_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.sample_operation.read_geo_data_frame")
    def test_sample_operation_successful(self, mock_read_geo_data_frame, mock_local_assets):
        """Test successful sampling of features."""
        # Set up mock for LocalAssets context manager
        mock_item = Mock()
        mock_local_asset_paths = {"asset1": "/tmp/asset1.parquet"}
        mock_local_assets.return_value.__enter__.return_value = (mock_item, mock_local_asset_paths)

        # Create a mock GeoDataFrame with points and additional columns
        points = [
            shapely.Point(0, 0),
            shapely.Point(1, 1),
            shapely.Point(2, 2),
            shapely.Point(3, 3),
            shapely.Point(4, 4),
        ]
        data = {
            "id": [1, 2, 3, 4, 5],
            "name": ["Point A", "Point B", "Point C", "Point D", "Point E"],
            "value": [10.5, 20.3, 15.7, 8.2, 12.9],
        }
        mock_gdf = gpd.GeoDataFrame(data, geometry=points)
        mock_gdf.crs = "EPSG:4326"
        mock_read_geo_data_frame.return_value = mock_gdf

        # Call the operation function
        result = sample_operation(
            dataset_georef=self.dataset_georef, number_of_features=self.number_of_features, workspace=self.mock_workspace
        )

        # Verify the result contains expected text
        self.assertIn("Sample of 3 features", result)
        self.assertIn("Columns: id, name, value, geometry", result)
        self.assertIn("Feature 0:", result)
        self.assertIn("id: 1", result)
        self.assertIn("name: Point A", result)
        self.assertIn("value: 10.5", result)

        # Verify the mocks were called
        mock_local_assets.assert_called_once()
        mock_read_geo_data_frame.assert_called_once()

    @patch("aws.osml.geoagents.spatial.sample_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.sample_operation.read_geo_data_frame")
    def test_sample_operation_default_number(self, mock_read_geo_data_frame, mock_local_assets):
        """Test sampling with default number of features."""
        # Set up mock for LocalAssets context manager
        mock_item = Mock()
        mock_local_asset_paths = {"asset1": "/tmp/asset1.parquet"}
        mock_local_assets.return_value.__enter__.return_value = (mock_item, mock_local_asset_paths)

        # Create a mock GeoDataFrame with points
        points = [shapely.Point(i, i) for i in range(15)]
        mock_gdf = gpd.GeoDataFrame(geometry=points)
        mock_gdf.crs = "EPSG:4326"
        mock_read_geo_data_frame.return_value = mock_gdf

        # Call the operation function with None for number_of_features
        result = sample_operation(dataset_georef=self.dataset_georef, number_of_features=None, workspace=self.mock_workspace)

        # Verify the result contains expected text for default 10 features
        self.assertIn("Sample of 10 features", result)

        # Verify the mocks were called
        mock_local_assets.assert_called_once()
        mock_read_geo_data_frame.assert_called_once()


if __name__ == "__main__":
    unittest.main()
