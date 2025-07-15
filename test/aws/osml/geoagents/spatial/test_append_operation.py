#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
import shapely
from pystac import Item

from aws.osml.geoagents.common import GeoDataReference, STACReference, Workspace
from aws.osml.geoagents.spatial.append_operation import append_operation


class TestAppendOperation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock workspace
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = "/tmp"

        # Create mock GeoDataReference instances
        self.dataset1_reference = Mock(spec=GeoDataReference)
        self.dataset1_reference.reference_string = "stac:test-dataset1#data"
        self.dataset1_reference.is_stac_reference = Mock(return_value=True)

        self.dataset2_reference = Mock(spec=GeoDataReference)
        self.dataset2_reference.reference_string = "stac:test-dataset2#data"
        self.dataset2_reference.is_stac_reference = Mock(return_value=True)

        self.dataset3_reference = Mock(spec=GeoDataReference)
        self.dataset3_reference.reference_string = "stac:test-dataset3#data"
        self.dataset3_reference.is_stac_reference = Mock(return_value=True)

        # Create a mock function name
        self.function_name = "APPEND"

    def create_test_geodataframes(self):
        """Create real geodataframes for testing."""
        # First geodataframe with point geometries
        points = [shapely.Point(0, 0), shapely.Point(1, 1), shapely.Point(2, 2)]
        gdf1 = gpd.GeoDataFrame(
            {"id": [1, 2, 3], "name": ["Point A", "Point B", "Point C"]}, geometry=points, crs="EPSG:4326"
        )

        # Second geodataframe with polygon geometries
        polygons = [
            shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]),
            shapely.Polygon([(2, 2), (3, 2), (3, 3), (2, 3), (2, 2)]),
        ]
        gdf2 = gpd.GeoDataFrame({"id": [4, 5], "name": ["Polygon A", "Polygon B"]}, geometry=polygons, crs="EPSG:4326")

        # Third geodataframe with linestring geometries
        lines = [shapely.LineString([(0, 0), (1, 1)]), shapely.LineString([(2, 2), (3, 3)])]
        gdf3 = gpd.GeoDataFrame({"id": [6, 7], "name": ["Line A", "Line B"]}, geometry=lines, crs="EPSG:4326")

        return gdf1, gdf2, gdf3

    @patch("aws.osml.geoagents.spatial.append_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.append_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.append_operation.create_stac_item_for_dataset")
    @patch("aws.osml.geoagents.spatial.append_operation.STACReference")
    def test_append_operation_successful(
        self, mock_stac_reference, mock_create_stac_item_for_dataset, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test successful appending of multiple geodataframes."""
        # Create real geodataframes
        gdf1, gdf2, gdf3 = self.create_test_geodataframes()

        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"data": Path("/tmp/asset1.parquet")}

        mock_item2 = Mock(spec=Item)
        mock_item2.properties = {"title": "Test Dataset 2"}
        mock_local_asset_paths2 = {"data": Path("/tmp/asset2.parquet")}

        mock_item3 = Mock(spec=Item)
        mock_item3.properties = {"title": "Test Dataset 3"}
        mock_local_asset_paths3 = {"data": Path("/tmp/asset3.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item1, mock_local_asset_paths1),
            (mock_item2, mock_local_asset_paths2),
            (mock_item3, mock_local_asset_paths3),
        ]

        # Configure read_geo_data_frame to return different GeoDataFrames on each call
        self.mock_workspace.read_geo_data_frame.side_effect = [gdf1, gdf2, gdf3]

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item1

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Call the operation function
        result = append_operation(
            dataset_references=[self.dataset1_reference, self.dataset2_reference, self.dataset3_reference],
            workspace=self.mock_workspace,
            function_name=self.function_name,
        )

        # Verify the result contains expected text
        self.assertIn("combined", result)
        self.assertIn("3 datasets", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 3)
        self.assertEqual(self.mock_workspace.read_geo_data_frame.call_count, 3)
        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()

        # Verify the write_geo_data_frame was called with a GeoDataFrame that has the expected number of rows
        # The combined GeoDataFrame should have 7 rows (3 from gdf1 + 2 from gdf2 + 2 from gdf3)
        args, kwargs = self.mock_workspace.write_geo_data_frame.call_args
        self.assertEqual(len(args), 2)  # Should have path and GeoDataFrame
        self.assertIsInstance(args[1], gpd.GeoDataFrame)
        self.assertEqual(len(args[1]), 7)  # 3 + 2 + 2 = 7 rows

    @patch("aws.osml.geoagents.spatial.append_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.append_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.append_operation.create_stac_item_for_dataset")
    @patch("aws.osml.geoagents.spatial.append_operation.STACReference")
    def test_append_operation_single_dataset(
        self, mock_stac_reference, mock_create_stac_item_for_dataset, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test appending a single dataset (should return the dataset unchanged)."""
        # Create real geodataframes
        gdf1, _, _ = self.create_test_geodataframes()

        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"data": Path("/tmp/asset1.parquet")}

        # Configure the LocalAssets mock
        mock_local_assets.return_value.__enter__.return_value = (mock_item1, mock_local_asset_paths1)

        # Configure read_geo_data_frame to return the GeoDataFrame
        self.mock_workspace.read_geo_data_frame.return_value = gdf1

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item1

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Call the operation function with a single dataset
        result = append_operation(
            dataset_references=[self.dataset1_reference],
            workspace=self.mock_workspace,
            function_name=self.function_name,
        )

        # Verify the result contains expected text
        self.assertIn("combined", result)
        self.assertIn("1 datasets", result)

        # Verify the mocks were called
        mock_local_assets.assert_called_once()
        self.mock_workspace.read_geo_data_frame.assert_called_once()
        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()

        # Verify the write_geo_data_frame was called with a GeoDataFrame that has the expected number of rows
        args, kwargs = self.mock_workspace.write_geo_data_frame.call_args
        self.assertEqual(len(args), 2)  # Should have path and GeoDataFrame
        self.assertIsInstance(args[1], gpd.GeoDataFrame)
        self.assertEqual(len(args[1]), 3)  # Original dataset has 3 rows

    def test_append_operation_no_datasets(self):
        """Test appending with no datasets (should raise ValueError)."""
        # Call the operation function with an empty list
        with self.assertRaises(ValueError):
            append_operation(
                dataset_references=[],
                workspace=self.mock_workspace,
                function_name=self.function_name,
            )

    @patch("aws.osml.geoagents.spatial.append_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.append_operation.create_stac_item_for_dataset")
    def test_append_operation_incompatible_crs(self, mock_create_stac_item_for_dataset, mock_local_assets):
        """Test appending datasets with incompatible CRS."""
        # Create real geodataframes with different CRS
        gdf1, _, _ = self.create_test_geodataframes()

        # Create a geodataframe with a different CRS
        points = [shapely.Point(0, 0), shapely.Point(1, 1)]
        gdf2 = gpd.GeoDataFrame(
            {"id": [4, 5], "name": ["Point D", "Point E"]}, geometry=points, crs="EPSG:3857"  # Different CRS
        )

        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"data": Path("/tmp/asset1.parquet")}

        mock_item2 = Mock(spec=Item)
        mock_item2.properties = {"title": "Test Dataset 2"}
        mock_local_asset_paths2 = {"data": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item1, mock_local_asset_paths1),
            (mock_item2, mock_local_asset_paths2),
        ]

        # Configure read_geo_data_frame to return different GeoDataFrames on each call
        self.mock_workspace.read_geo_data_frame.side_effect = [gdf1, gdf2]

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.side_effect = [mock_item1, mock_item2]

        # Call the operation function with incompatible CRS
        with self.assertRaises(ValueError):
            append_operation(
                dataset_references=[self.dataset1_reference, self.dataset2_reference],
                workspace=self.mock_workspace,
                function_name=self.function_name,
            )


if __name__ == "__main__":
    unittest.main()
