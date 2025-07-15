#  Copyright 2025 Amazon.com, Inc. or its affiliates.

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import geopandas as gpd
import shapely
from pyproj import CRS
from pystac import Asset, Item

from aws.osml.geoagents.common import GeoDataReference, STACReference, Workspace
from aws.osml.geoagents.spatial.cluster_operation import cluster_operation


class TestClusterOperation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock workspace
        self.mock_workspace = Mock(spec=Workspace)
        self.mock_workspace.session_local_path = "/tmp"

        # Create a mock GeoDataReference
        self.dataset_reference = Mock(spec=GeoDataReference)
        self.dataset_reference.reference_string = "stac:test-dataset"
        self.dataset_reference.is_stac_reference = Mock(return_value=True)

        # Create a mock function name
        self.function_name = "CLUSTER"

        # Create a mock distance
        self.distance_meters = 100.0

        # Create a mock max_clusters
        self.max_clusters = 3

        # Create a sample STAC item
        self.sample_item = Item(
            id="1234",
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]},
            datetime=datetime.fromisoformat("2025-04-23T14:05:23Z"),
            bbox=[0, 0, 2, 2],
            properties={
                "title": "Test Dataset",
                "keywords": ["test"],
            },
            assets={"data": Asset(href="s3://fake-test-bucket/data.parquet")},
        )

    def _create_clustered_geodataframe(self, with_clusters=True):
        """
        Helper method to create a GeoDataFrame with points that will form clusters.

        :param with_clusters: If True, creates points that will form clusters; if False, creates scattered points
        :return: A GeoDataFrame with point geometries
        """
        if with_clusters:
            # Create three distinct clusters of points, 100m is slightly less than 0.001 degrees at the equator
            cluster1 = [(0.1, 0.1), (0.1002, 0.1001), (0.1001, 0.1003), (0.0999, 0.1002)]  # Cluster 1
            cluster2 = [(0.5, 0.5), (0.5001, 0.5002), (0.4999, 0.5001), (0.5002, 0.4999), (0.5002, 0.5001)]  # Cluster 2
            cluster3 = [(0.9, 0.9), (0.9001, 0.9002), (0.8999, 0.9001)]  # Cluster 3

            # Add some noise points
            noise = [(0.3, 0.7), (0.7, 0.3)]

            all_points = cluster1 + cluster2 + cluster3 + noise
        else:
            # Create scattered points that won't form clusters with the default distance
            all_points = [(0.1, 0.1), (0.3, 0.3), (0.5, 0.5), (0.7, 0.7), (0.9, 0.9)]

        # Create geometries
        geometries = [shapely.geometry.Point(x, y) for x, y in all_points]

        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(geometry=geometries)
        gdf.set_crs(CRS.from_epsg(4326), inplace=True)

        return gdf

    @patch("aws.osml.geoagents.spatial.cluster_operation.LocalAssets")
    @patch("aws.osml.geoagents.spatial.cluster_operation.create_derived_stac_item")
    @patch("aws.osml.geoagents.spatial.cluster_operation.create_stac_item_for_dataset")
    @patch("aws.osml.geoagents.spatial.cluster_operation.STACReference")
    def test_cluster_operation_successful(
        self, mock_stac_reference, mock_create_stac_item_for_dataset, mock_create_derived_stac_item, mock_local_assets
    ):
        """Test successful clustering of features."""
        # Set up mock for LocalAssets context manager
        mock_local_asset_paths = {"asset1": Path("/tmp/asset1.parquet")}
        mock_local_assets.return_value.__enter__.return_value = (self.sample_item, mock_local_asset_paths)

        # Create a mock GeoDataFrame with points that can be clustered
        mock_gdf = self._create_clustered_geodataframe(with_clusters=True)
        self.mock_workspace.read_geo_data_frame.return_value = mock_gdf

        # Set up mock for create_derived_stac_item
        mock_derived_item = Mock(spec=Item)
        mock_create_derived_stac_item.return_value = mock_derived_item

        # Set up mock for create_stac_item_for_dataset
        mock_create_stac_item_for_dataset.return_value = self.sample_item

        # Set up mock for STACReference
        mock_stac_ref = Mock(spec=STACReference)
        mock_stac_ref.item_id = "test-item-id"
        mock_stac_reference.new_from_timestamp.return_value = mock_stac_ref

        # Call the operation function
        result = cluster_operation(
            dataset_reference=self.dataset_reference,
            distance_meters=self.distance_meters,
            max_clusters=self.max_clusters,
            workspace=self.mock_workspace,
            function_name=self.function_name,
        )

        # Verify the result contains expected text
        self.assertIn("clusters", result)
        self.assertIn("distance threshold", result)

        # Verify the mocks were called
        mock_local_assets.assert_called_once()
        self.mock_workspace.read_geo_data_frame.assert_called_once()
        self.mock_workspace.write_geo_data_frame.assert_called()
        mock_create_derived_stac_item.assert_called_once()
        self.mock_workspace.create_item.assert_called_once()


if __name__ == "__main__":
    unittest.main()
