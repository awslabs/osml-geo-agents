#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
import shapely
from pystac import Item

from aws.osml.geoagents.common import GeoDataReference, STACReference, Workspace
from aws.osml.geoagents.spatial.filter_operation import filter_operation


class TestFilterOperation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock workspace
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = "/tmp"

        # Create a mock GeoDataReference
        self.dataset_reference = Mock(spec=GeoDataReference)
        # Set up the reference_string property
        self.dataset_reference.reference_string = "stac:test-dataset"
        # Set up the is_stac_reference method to return True
        self.dataset_reference.is_stac_reference = Mock(return_value=True)

        # Create a mock function name
        self.function_name = "FILTER"

        # Create a mock filter bounds
        self.filter_bounds = shapely.Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])

    @patch("aws.osml.geoagents.spatial.filter_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.filter_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.filter_operation.create_stac_item_for_dataset")
    @patch("aws.osml.geoagents.spatial.filter_operation.STACReference")
    def test_filter_operation_successful(
        self, mock_stac_reference, mock_create_stac_item_for_dataset, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test successful filtering of features."""
        # Set up mock for LocalAssets context manager
        mock_item = Mock(spec=Item)
        mock_item.properties = {"title": "Test Dataset"}
        mock_local_asset_paths = {"asset1": Path("/tmp/asset1.parquet")}
        mock_local_assets.return_value.__enter__.return_value = (mock_item, mock_local_asset_paths)

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = mock_item

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Create a mock GeoDataFrame with points, some inside and some outside the filter bounds
        points = [
            shapely.Point(0.5, 0.5),  # Inside the filter bounds
            shapely.Point(1.5, 1.5),  # Outside the filter bounds
            shapely.Point(0.2, 0.2),  # Inside the filter bounds
        ]
        mock_gdf = gpd.GeoDataFrame(geometry=points)
        mock_gdf.crs = "EPSG:4326"

        # Set up the intersects method to return True for points inside the filter bounds
        # and False for points outside
        mock_gdf["intersects_result"] = [True, False, True]
        mock_gdf.intersects = Mock(return_value=mock_gdf["intersects_result"])

        self.mock_workspace.read_geo_data_frame.return_value = mock_gdf

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Call the operation function
        result = filter_operation(
            dataset_reference=self.dataset_reference,
            filter_bounds=self.filter_bounds,
            workspace=self.mock_workspace,
            function_name=self.function_name,
        )

        # Verify the result contains expected text
        self.assertIn("filtered", result)
        self.assertIn("boundary", result)

        # Verify the mocks were called
        mock_local_assets.assert_called_once()
        self.mock_workspace.read_geo_data_frame.assert_called_once()
        self.mock_workspace.write_geo_data_frame.assert_called_once()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
