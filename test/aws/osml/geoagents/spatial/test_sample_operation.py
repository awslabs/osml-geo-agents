#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from unittest.mock import Mock, patch

import geopandas as gpd
import shapely

from aws.osml.geoagents.common import GeoDataReference, Workspace
from aws.osml.geoagents.spatial.sample_operation import sample_operation


class TestSampleOperation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock workspace
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = "/tmp"

        # Create a mock GeoDataReference
        self.dataset_reference = Mock(spec=GeoDataReference)
        self.dataset_reference.reference_string = "stac:test-dataset"
        self.dataset_reference.is_stac_reference = Mock(return_value=True)

        # Create mock number of features
        self.number_of_features = 3

    @patch("aws.osml.geoagents.spatial.sample_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.sample_operation.create_stac_item_for_dataset")
    def test_sample_operation_successful(self, mock_create_stac_item_for_dataset, mock_local_assets):
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
        self.mock_workspace.read_geo_data_frame.return_value = mock_gdf

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item

        # Call the operation function
        result = sample_operation(
            dataset_reference=self.dataset_reference,
            number_of_features=self.number_of_features,
            workspace=self.mock_workspace,
        )

        # Verify the result contains expected text
        self.assertIn("Sample of 3 features", result)

        # Verify markdown table format
        self.assertIn("| id | name | value | geometry |", result)
        self.assertIn("| --", result)  # Separator row
        self.assertIn("| 1 | Point A | 10.5 |", result)

        # Verify the mocks were called
        mock_local_assets.assert_called_once()
        self.mock_workspace.read_geo_data_frame.assert_called_once()

    @patch("aws.osml.geoagents.spatial.sample_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.sample_operation.create_stac_item_for_dataset")
    def test_sample_operation_default_number(self, mock_create_stac_item_for_dataset, mock_local_assets):
        """Test sampling with default number of features."""
        # Set up mock for LocalAssets context manager
        mock_item = Mock()
        mock_local_asset_paths = {"asset1": "/tmp/asset1.parquet"}
        mock_local_assets.return_value.__enter__.return_value = (mock_item, mock_local_asset_paths)

        # Create a mock GeoDataFrame with points
        points = [shapely.Point(i, i) for i in range(15)]
        mock_gdf = gpd.GeoDataFrame(geometry=points)
        mock_gdf.crs = "EPSG:4326"
        self.mock_workspace.read_geo_data_frame.return_value = mock_gdf

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item

        # Call the operation function with None for number_of_features
        result = sample_operation(
            dataset_reference=self.dataset_reference, number_of_features=None, workspace=self.mock_workspace
        )

        # Verify the result contains expected text for default 10 features
        self.assertIn("Sample of 10 features", result)

        # Verify markdown table format
        self.assertIn("| geometry |", result)
        self.assertIn("| --", result)  # Separator row

        # Verify the mocks were called
        mock_local_assets.assert_called_once()
        self.mock_workspace.read_geo_data_frame.assert_called_once()

    @patch("aws.osml.geoagents.spatial.sample_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.sample_operation.create_stac_item_for_dataset")
    def test_sample_operation_max_features_limit(self, mock_create_stac_item_for_dataset, mock_local_assets):
        """Test that the number of features is capped at 20."""
        # Set up mock for LocalAssets context manager
        mock_item = Mock()
        mock_local_asset_paths = {"asset1": "/tmp/asset1.parquet"}
        mock_local_assets.return_value.__enter__.return_value = (mock_item, mock_local_asset_paths)

        # Create a mock GeoDataFrame with 30 points
        points = [shapely.Point(i, i) for i in range(30)]
        mock_gdf = gpd.GeoDataFrame(geometry=points)
        mock_gdf.crs = "EPSG:4326"
        self.mock_workspace.read_geo_data_frame.return_value = mock_gdf

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item

        # Call the operation function with a number greater than the max limit (20)
        result = sample_operation(
            dataset_reference=self.dataset_reference, number_of_features=30, workspace=self.mock_workspace
        )

        # Verify the result contains exactly 20 features (the maximum allowed)
        self.assertIn("Sample of 20 features", result)

        # Verify the mocks were called
        mock_local_assets.assert_called_once()
        self.mock_workspace.read_geo_data_frame.assert_called_once()

    @patch("aws.osml.geoagents.spatial.sample_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.sample_operation.create_stac_item_for_dataset")
    def test_sample_operation_with_max_width(self, mock_create_stac_item_for_dataset, mock_local_assets):
        """Test sampling with custom max_column_width."""
        # Set up mock for LocalAssets context manager
        mock_item = Mock()
        mock_local_asset_paths = {"asset1": "/tmp/asset1.parquet"}
        mock_local_assets.return_value.__enter__.return_value = (mock_item, mock_local_asset_paths)

        # Create a mock GeoDataFrame with points and additional columns
        points = [
            shapely.Point(0, 0),
            shapely.Point(1, 1),
        ]
        data = {
            "id": [1, 2],
            "name": ["This is a very long name that should be truncated", "Another long name for testing truncation"],
            "value": [10.5, 20.3],
        }
        mock_gdf = gpd.GeoDataFrame(data, geometry=points)
        mock_gdf.crs = "EPSG:4326"
        self.mock_workspace.read_geo_data_frame.return_value = mock_gdf

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item

        # Call the operation function with custom max_column_width
        result = sample_operation(
            dataset_reference=self.dataset_reference,
            number_of_features=2,
            workspace=self.mock_workspace,
            max_column_width=10,
        )

        # Verify truncation in the result
        self.assertIn("| This is...", result)
        self.assertIn("| Another...", result)

        # Verify the mocks were called
        mock_local_assets.assert_called_once()
        self.mock_workspace.read_geo_data_frame.assert_called_once()


if __name__ == "__main__":
    unittest.main()
