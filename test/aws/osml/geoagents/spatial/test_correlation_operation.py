#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
import shapely
from pystac import Item

from aws.osml.geoagents.common import Georeference, Workspace
from aws.osml.geoagents.spatial.correlation_operation import CorrelationTypes, correlation_operation


class TestCorrelationOperation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock workspace
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = "/tmp"

        # Create mock georeferences
        self.dataset1_georef = Mock(spec=Georeference)
        self.dataset2_georef = Mock(spec=Georeference)

        # Create a mock function name
        self.function_name = "CORRELATE"

        # Create a mock distance
        self.distance = 100.0

        # Create mock geo column names
        self.dataset1_geo_column = "geometry"
        self.dataset2_geo_column = "geometry"

    @patch("aws.osml.geoagents.spatial.correlation_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_operation.read_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.correlation_operation.write_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_derived_stac_item")
    def test_correlation_operation_intersection(
        self, mock_create_derived_stac_item, mock_write_geo_data_frame, mock_read_geo_data_frame, mock_local_assets
    ):
        """Test successful intersection correlation."""
        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"asset1": Path("/tmp/asset1.parquet")}

        mock_item2 = Mock(spec=Item)
        mock_item2.properties = {"title": "Test Dataset 2"}
        mock_local_asset_paths2 = {"asset2": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item1, mock_local_asset_paths1),
            (mock_item2, mock_local_asset_paths2),
        ]

        # Create mock GeoDataFrames with overlapping polygons
        polygon1 = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        polygon2 = shapely.Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)])

        gdf1 = gpd.GeoDataFrame(geometry=[polygon1])
        gdf1.crs = "EPSG:4326"

        gdf2 = gpd.GeoDataFrame(geometry=[polygon2])
        gdf2.crs = "EPSG:4326"

        # Configure read_geo_data_frame to return different GeoDataFrames on each call
        mock_read_geo_data_frame.side_effect = [gdf1, gdf2]

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Call the operation function with INTERSECTION correlation type
        result = correlation_operation(
            dataset1_georef=self.dataset1_georef,
            dataset2_georef=self.dataset2_georef,
            correlation_type=CorrelationTypes.INTERSECTION,
            distance=self.distance,
            dataset1_geo_column=self.dataset1_geo_column,
            dataset2_geo_column=self.dataset2_geo_column,
            workspace=self.mock_workspace,
            function_name=self.function_name,
        )

        # Verify the result contains expected text
        self.assertIn("correlated", result)
        self.assertIn("intersection", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(mock_read_geo_data_frame.call_count, 2)
        mock_write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.publish_item.assert_called_once()

    @patch("aws.osml.geoagents.spatial.correlation_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.correlation_operation.read_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.correlation_operation.write_geo_data_frame")
    @patch("aws.osml.geoagents.spatial.correlation_operation.create_derived_stac_item")
    def test_correlation_operation_difference(
        self, mock_create_derived_stac_item, mock_write_geo_data_frame, mock_read_geo_data_frame, mock_local_assets
    ):
        """Test successful difference correlation."""
        # Set up mocks for LocalAssets context manager
        mock_item1 = Mock(spec=Item)
        mock_item1.properties = {"title": "Test Dataset 1"}
        mock_local_asset_paths1 = {"asset1": Path("/tmp/asset1.parquet")}

        mock_item2 = Mock(spec=Item)
        mock_item2.properties = {"title": "Test Dataset 2"}
        mock_local_asset_paths2 = {"asset2": Path("/tmp/asset2.parquet")}

        # Configure the LocalAssets mock to return different values on each call
        mock_local_assets.return_value.__enter__.side_effect = [
            (mock_item1, mock_local_asset_paths1),
            (mock_item2, mock_local_asset_paths2),
        ]

        # Create mock GeoDataFrames with overlapping polygons
        polygon1 = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        polygon2 = shapely.Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5), (0.5, 0.5)])

        gdf1 = gpd.GeoDataFrame(geometry=[polygon1])
        gdf1.crs = "EPSG:4326"

        gdf2 = gpd.GeoDataFrame(geometry=[polygon2])
        gdf2.crs = "EPSG:4326"

        # Configure read_geo_data_frame to return different GeoDataFrames on each call
        mock_read_geo_data_frame.side_effect = [gdf1, gdf2]

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Call the operation function with DIFFERENCE correlation type
        result = correlation_operation(
            dataset1_georef=self.dataset1_georef,
            dataset2_georef=self.dataset2_georef,
            correlation_type=CorrelationTypes.DIFFERENCE,
            distance=self.distance,
            dataset1_geo_column=self.dataset1_geo_column,
            dataset2_geo_column=self.dataset2_geo_column,
            workspace=self.mock_workspace,
            function_name=self.function_name,
        )

        # Verify the result contains expected text
        self.assertIn("correlated", result)
        self.assertIn("difference", result)

        # Verify the mocks were called
        self.assertEqual(mock_local_assets.call_count, 2)
        self.assertEqual(mock_read_geo_data_frame.call_count, 2)
        mock_write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.publish_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
