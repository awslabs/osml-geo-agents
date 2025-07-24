#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
import shapely
from pystac import Item

from aws.osml.geoagents.common import GeoDataReference, STACReference, Workspace
from aws.osml.geoagents.spatial.filter_operation import FilterTypes, filter_operation


class TestFilterOperation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock workspace
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = "/tmp"

        # Create mock GeoDataReferences
        self.dataset_reference = Mock(spec=GeoDataReference)
        self.dataset_reference.reference_string = "stac:test-dataset"
        self.dataset_reference.is_stac_reference = Mock(return_value=True)

        self.filter_reference = Mock(spec=GeoDataReference)
        self.filter_reference.reference_string = "stac:test-filter"
        self.filter_reference.is_stac_reference = Mock(return_value=True)

        # Create a mock function name
        self.function_name = "FILTER"

        # Create mock geo column names
        self.dataset_geo_column = "geometry"
        self.filter_geo_column = "geometry"

    @patch("aws.osml.geoagents.spatial.filter_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.filter_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.filter_operation.load_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.filter_operation.STACReference")
    def test_filter_operation_intersects(
        self, mock_stac_reference, mock_load_geo_data_frame, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test successful filtering of features using INTERSECTS filter type."""
        # Set up mocks for LocalAssets context manager
        mock_item = Mock(spec=Item)
        mock_item.properties = {"title": "Test Dataset"}
        mock_local_asset_paths = {"asset1": Path("/tmp/asset1.parquet")}

        mock_filter_item = Mock(spec=Item)
        mock_filter_item.properties = {"title": "Test Filter Dataset"}
        mock_filter_asset_paths = {"asset2": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item, mock_local_asset_paths),
            (mock_filter_item, mock_filter_asset_paths),
        ]

        # Create mock GeoDataFrames with points
        points = [
            shapely.Point(0.5, 0.5),
            shapely.Point(1.5, 1.5),
            shapely.Point(0.2, 0.2),
        ]
        mock_gdf = gpd.GeoDataFrame(geometry=points)
        mock_gdf.crs = "EPSG:4326"

        filter_points = [
            shapely.Point(0.5, 0.5),  # Matches first point
            shapely.Point(0.2, 0.2),  # Matches third point
        ]
        mock_filter_gdf = gpd.GeoDataFrame(geometry=filter_points)
        mock_filter_gdf.crs = "EPSG:4326"

        # Configure load_geo_data_frame to return different values on each call
        mock_load_geo_data_frame.side_effect = [
            (mock_gdf, mock_item, "asset1"),
            (mock_filter_gdf, mock_filter_item, "asset2"),
        ]

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Call the operation function with INTERSECTS filter type
        result = filter_operation(
            dataset_reference=self.dataset_reference,
            filter_reference=self.filter_reference,
            filter_type=FilterTypes.INTERSECTS,
            workspace=self.mock_workspace,
            function_name=self.function_name,
            dataset_geo_column=self.dataset_geo_column,
            filter_geo_column=self.filter_geo_column,
        )

        # Verify the result contains expected text
        self.assertIn("filtered", result)
        self.assertIn("intersects", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(mock_load_geo_data_frame.call_count, 2)

        # Verify load_geo_data_frame was called with correct parameters
        mock_load_geo_data_frame.assert_any_call(
            mock_local_asset_paths, self.mock_workspace, self.dataset_reference, mock_item, self.dataset_geo_column
        )
        mock_load_geo_data_frame.assert_any_call(
            mock_filter_asset_paths, self.mock_workspace, self.filter_reference, mock_filter_item, self.filter_geo_column
        )

        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()

    @patch("aws.osml.geoagents.spatial.filter_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.filter_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.filter_operation.load_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.filter_operation.STACReference")
    def test_filter_operation_difference(
        self, mock_stac_reference, mock_load_geo_data_frame, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test successful filtering of features using DIFFERENCE filter type."""
        # Set up mocks for LocalAssets context manager
        mock_item = Mock(spec=Item)
        mock_item.properties = {"title": "Test Dataset"}
        mock_local_asset_paths = {"asset1": Path("/tmp/asset1.parquet")}

        mock_filter_item = Mock(spec=Item)
        mock_filter_item.properties = {"title": "Test Filter Dataset"}
        mock_filter_asset_paths = {"asset2": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item, mock_local_asset_paths),
            (mock_filter_item, mock_filter_asset_paths),
        ]

        # Create mock GeoDataFrames with points
        points = [
            shapely.Point(0.5, 0.5),
            shapely.Point(1.5, 1.5),
            shapely.Point(0.2, 0.2),
        ]
        mock_gdf = gpd.GeoDataFrame(geometry=points)
        mock_gdf.crs = "EPSG:4326"

        filter_points = [
            shapely.Point(0.5, 0.5),  # Matches first point
            shapely.Point(0.2, 0.2),  # Matches third point
        ]
        mock_filter_gdf = gpd.GeoDataFrame(geometry=filter_points)
        mock_filter_gdf.crs = "EPSG:4326"

        # Configure load_geo_data_frame to return different values on each call
        mock_load_geo_data_frame.side_effect = [
            (mock_gdf, mock_item, "asset1"),
            (mock_filter_gdf, mock_filter_item, "asset2"),
        ]

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Call the operation function with DIFFERENCE filter type
        result = filter_operation(
            dataset_reference=self.dataset_reference,
            filter_reference=self.filter_reference,
            filter_type=FilterTypes.DIFFERENCE,
            workspace=self.mock_workspace,
            function_name=self.function_name,
            dataset_geo_column=self.dataset_geo_column,
            filter_geo_column=self.filter_geo_column,
        )

        # Verify the result contains expected text
        self.assertIn("filtered", result)
        self.assertIn("difference", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(mock_load_geo_data_frame.call_count, 2)

        # Verify load_geo_data_frame was called with correct parameters
        mock_load_geo_data_frame.assert_any_call(
            mock_local_asset_paths, self.mock_workspace, self.dataset_reference, mock_item, self.dataset_geo_column
        )
        mock_load_geo_data_frame.assert_any_call(
            mock_filter_asset_paths, self.mock_workspace, self.filter_reference, mock_filter_item, self.filter_geo_column
        )

        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
